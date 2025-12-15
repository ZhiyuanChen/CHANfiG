#include <Python.h>

/*
 * C extension helpers for CHANfiG.
 *
 * Currently provides:
 * - find_placeholders(text: str) -> list[str]
 *   Finds placeholders of the form ${...}, including nested placeholders,
 *   mirroring chanfig.utils.placeholder.find_placeholders.
 *
 * - FlatDictCore: dict subclass with attribute-style access and annotation-aware set.
 */

static int
find_placeholders_impl(PyObject *text, PyObject *result)
{
    if (!PyUnicode_Check(text)) {
        return 0;
    }

    if (PyUnicode_READY(text) == -1) {
        return -1;
    }

    Py_ssize_t len = PyUnicode_GET_LENGTH(text);
    void *data = PyUnicode_DATA(text);
    int kind = PyUnicode_KIND(text);

    /* simple stack of start indices for "${" */
    Py_ssize_t *stack = PyMem_Malloc(sizeof(Py_ssize_t) * (len + 1));
    if (stack == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    Py_ssize_t top = 0;

    for (Py_ssize_t i = 0; i < len; ++i) {
        Py_UCS4 ch = PyUnicode_READ(kind, data, i);
        if (ch == '$' && i + 1 < len) {
            Py_UCS4 next = PyUnicode_READ(kind, data, i + 1);
            if (next == '{') {
                stack[top++] = i;
                ++i; /* skip '{' */
                continue;
            }
        } else if (ch == '}' && top > 0) {
            Py_ssize_t start = stack[--top];
            Py_ssize_t begin = start + 2; /* skip ${ */
            Py_ssize_t end = i;
            PyObject *placeholder = PyUnicode_Substring(text, begin, end);
            if (placeholder == NULL) {
                PyMem_Free(stack);
                return -1;
            }
            if (top == 0) {
                if (PyList_Append(result, placeholder) == -1) {
                    Py_DECREF(placeholder);
                    PyMem_Free(stack);
                    return -1;
                }
                /* recursively find nested placeholders */
                if (find_placeholders_impl(placeholder, result) == -1) {
                    Py_DECREF(placeholder);
                    PyMem_Free(stack);
                    return -1;
                }
            }
            Py_DECREF(placeholder);
        }
    }

    PyMem_Free(stack);
    return 0;
}

static PyObject *
py_find_placeholders(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"text", NULL};
    PyObject *text = NULL;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O:find_placeholders", kwlist, &text)) {
        return NULL;
    }

    PyObject *result = PyList_New(0);
    if (result == NULL) {
        return NULL;
    }

    if (find_placeholders_impl(text, result) == -1) {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

/* forward declaration of method table */
static PyMethodDef ChanfigMethods[];

/* ---------------- FlatDictCore ---------------- */

typedef struct {
    PyDictObject dict;
} FlatDictCore;

/* lazily imported helpers */
static PyObject *VariableType = NULL;
static PyObject *VariableClass = NULL;
static PyObject *get_cached_annotations_fn = NULL;
static PyObject *honor_annotation_fn = NULL;
static PyObject *find_circular_reference_fn = NULL;

static int
ensure_helpers(void)
{
    if (get_cached_annotations_fn && honor_annotation_fn && VariableType) {
        return 0;
    }
    PyObject *mod = PyImport_ImportModule("chanfig.utils.annotation");
    if (!mod) return -1;
    get_cached_annotations_fn = PyObject_GetAttrString(mod, "get_cached_annotations");
    honor_annotation_fn = PyObject_GetAttrString(mod, "honor_annotation");
    Py_DECREF(mod);
    if (!get_cached_annotations_fn || !honor_annotation_fn) return -1;

    PyObject *var_mod = PyImport_ImportModule("chanfig.variable");
    if (!var_mod) return -1;
    VariableType = PyObject_GetAttrString(var_mod, "Variable");
    VariableClass = VariableType;
    Py_DECREF(var_mod);
    if (!VariableType) return -1;

    return 0;
}

static int
ensure_placeholder_helpers(void)
{
    if (find_circular_reference_fn) {
        return 0;
    }
    PyObject *mod = PyImport_ImportModule("chanfig.utils.placeholder");
    if (!mod) return -1;
    find_circular_reference_fn = PyObject_GetAttrString(mod, "find_circular_reference");
    Py_DECREF(mod);
    if (!find_circular_reference_fn) return -1;
    return 0;
}

static int
FlatDictCore_set_item(PyObject *self, PyObject *key, PyObject *value)
{
    /* Null key check */
    PyObject *null_obj = PyImport_ImportModule("chanfig.utils.null");
    if (null_obj) {
        PyObject *Null = PyObject_GetAttrString(null_obj, "Null");
        Py_DECREF(null_obj);
        if (Null && value && PyObject_RichCompareBool(key, Null, Py_EQ) == 1) {
            Py_DECREF(Null);
            PyErr_SetString(PyExc_ValueError, "name must not be null");
            return -1;
        }
        Py_XDECREF(Null);
    }

    /* Variable handling: if existing value is Variable, call set */
    PyObject *existing = PyDict_GetItemWithError(self, key);
    if (existing && ensure_helpers() == 0 && VariableType) {
        int is_var = PyObject_IsInstance(existing, VariableType);
        if (is_var == 1) {
            PyObject *res = PyObject_CallMethod(existing, "set", "O", value);
            if (!res) return -1;
            Py_DECREF(res);
            return 0;
        } else if (is_var == -1) {
            return -1;
        }
    }

    /* annotation honoring */
    if (ensure_helpers() == 0 && get_cached_annotations_fn && honor_annotation_fn) {
        PyObject *annos = PyObject_CallFunctionObjArgs(get_cached_annotations_fn, self, NULL);
        if (annos) {
            PyObject *anno = PyObject_GetItem(annos, key);
            if (anno) {
                PyObject *new_value = PyObject_CallFunctionObjArgs(honor_annotation_fn, value, anno, NULL);
                if (!new_value) {
                    Py_DECREF(anno);
                    Py_DECREF(annos);
                    return -1;
                }
                value = new_value;
                Py_DECREF(anno);
                Py_DECREF(annos);
                /* fall through with potentially converted value */
                /* set with converted value */
                int res = PyDict_SetItem(self, key, value);
                Py_DECREF(value);
                return res;
            } else {
                PyErr_Clear(); /* no annotation for this key */
            }
            Py_DECREF(annos);
        } else {
            PyErr_Clear();
        }
    }

    return PyDict_SetItem(self, key, value);
}

static PyObject *
FlatDictCore_getattro(PyObject *self, PyObject *name);
static int
FlatDictCore_setattro(PyObject *self, PyObject *name, PyObject *value);

static PyObject *
FlatDictCore_subscript(PyObject *self, PyObject *key)
{
    PyObject *value = PyDict_GetItemWithError(self, key);
    if (value) {
        Py_INCREF(value);
        return value;
    }
    if (PyErr_Occurred()) {
        return NULL;
    }
    /* Key not found */
    PyErr_SetObject(PyExc_KeyError, key);
    return NULL;
}

static int
FlatDictCore_ass_subscript(PyObject *self, PyObject *key, PyObject *value)
{
    if (value == NULL) {
        return PyDict_DelItem(self, key);
    }
    return FlatDictCore_set_item(self, key, value);
}

static int
is_reserved_attr(PyObject *name_obj)
{
    if (!PyUnicode_Check(name_obj)) {
        return 1;
    }
    Py_ssize_t len;
    const char *name = PyUnicode_AsUTF8AndSize(name_obj, &len);
    if (name == NULL) {
        return 1;
    }
    /* reserve dunders and core helpers */
    if (len >= 4 && name[0] == '_' && name[1] == '_' && name[len - 2] == '_' && name[len - 1] == '_') {
        return 1;
    }
    if (strcmp(name, "keys") == 0 || strcmp(name, "values") == 0 || strcmp(name, "items") == 0 ||
        strcmp(name, "getattr") == 0 || strcmp(name, "setattr") == 0 || strcmp(name, "delattr") == 0 ||
        strcmp(name, "hasattr") == 0 || strcmp(name, "repr") == 0 || strcmp(name, "extra_repr") == 0) {
        return 1;
    }
    return 0;
}

static PyObject *
FlatDictCore_getattro(PyObject *self, PyObject *name)
{
    if (!is_reserved_attr(name) && PyDict_Contains(self, name)) {
        PyObject *value = PyDict_GetItemWithError(self, name);
        if (value) {
            Py_INCREF(value);
            return value;
        }
        if (PyErr_Occurred()) {
            return NULL;
        }
    }
    return PyObject_GenericGetAttr(self, name);
}

static int
FlatDictCore_setattro(PyObject *self, PyObject *name, PyObject *value)
{
    if (!is_reserved_attr(name)) {
        return FlatDictCore_set_item(self, name, value);
    }
    return PyObject_GenericSetAttr(self, name, value);
}

static int
has_dollar(PyObject *text)
{
    if (!PyUnicode_Check(text)) {
        return 0;
    }
    if (PyUnicode_READY(text) == -1) {
        return 0;
    }
    Py_ssize_t pos = PyUnicode_FindChar(text, '$', 0, PyUnicode_GET_LENGTH(text), 1);
    return pos != -1;
}

static int
adjust_placeholders(PyObject *key, PyObject *placeholders)
{
    /* adjust relative placeholders and self-references */
    if (!PyUnicode_Check(key)) {
        return 0;
    }
    Py_ssize_t plen = PyList_GET_SIZE(placeholders);
    for (Py_ssize_t i = 0; i < plen; ++i) {
        PyObject *name = PyList_GET_ITEM(placeholders, i);
        if (!PyUnicode_Check(name)) {
            return 0;
        }
        Py_INCREF(name);
        int updated = 0;
        if (PyUnicode_READY(name) == -1 || PyUnicode_READY(key) == -1) {
            Py_DECREF(name);
            return -1;
        }
        void *data = PyUnicode_DATA(name);
        int kind = PyUnicode_KIND(name);
        if (PyUnicode_GET_LENGTH(name) > 0 && PyUnicode_READ(kind, data, 0) == '.') {
            Py_ssize_t dot_pos = PyUnicode_FindChar(key, '.', 0, PyUnicode_GET_LENGTH(key), -1);
            PyObject *prefix = NULL;
            if (dot_pos == -1) {
                prefix = Py_NewRef(key);
            } else {
                prefix = PyUnicode_Substring(key, 0, dot_pos);
            }
            if (!prefix) {
                Py_DECREF(name);
                return -1;
            }
            PyObject *combined = PyUnicode_Concat(prefix, name);
            Py_DECREF(prefix);
            Py_DECREF(name);
            if (!combined) {
                return -1;
            }
            name = combined;
            updated = 1;
        }
        int eq = PyObject_RichCompareBool(name, key, Py_EQ);
        if (eq == -1) {
            Py_DECREF(name);
            return -1;
        }
        if (eq == 1) {
            PyErr_Format(PyExc_ValueError, "Cannot interpolate %U to itself.", key);
            Py_DECREF(name);
            return -1;
        }
        if (updated) {
            Py_DECREF(PyList_GET_ITEM(placeholders, i));
            PyList_SET_ITEM(placeholders, i, name); /* steals ref */
        } else {
            Py_DECREF(name);
        }
    }
    return 0;
}

static int
collect_placeholders(PyObject *mapping, PyObject **out_placeholders)
{
    PyObject *result = PyDict_New();
    if (!result) return -1;

    PyObject *items = PyMapping_Items(mapping);
    if (!items) {
        Py_DECREF(result);
        return -1;
    }

    Py_ssize_t len = PyList_GET_SIZE(items);
    for (Py_ssize_t i = 0; i < len; ++i) {
        PyObject *item = PyList_GET_ITEM(items, i); /* borrowed */
        PyObject *key = PyTuple_GET_ITEM(item, 0);
        PyObject *value = PyTuple_GET_ITEM(item, 1);

        if (!PyUnicode_Check(key)) {
            Py_DECREF(items);
            Py_DECREF(result);
            return 0; /* fallback to Python for non-string keys */
        }
        if (PyList_Check(value) || PyTuple_Check(value)) {
            Py_DECREF(items);
            Py_DECREF(result);
            return 0; /* fallback for list/tuple values */
        }
        if (PyMapping_Check(value) && !PyUnicode_Check(value)) {
            Py_DECREF(items);
            Py_DECREF(result);
            return 0; /* fallback for nested mappings */
        }
        if (!PyUnicode_Check(value) || !has_dollar(value)) {
            continue;
        }
        PyObject *placeholder_list = PyList_New(0);
        if (!placeholder_list) {
            Py_DECREF(items);
            Py_DECREF(result);
            return -1;
        }
        if (find_placeholders_impl(value, placeholder_list) == -1) {
            Py_DECREF(placeholder_list);
            Py_DECREF(items);
            Py_DECREF(result);
            return -1;
        }
        if (PyList_GET_SIZE(placeholder_list) == 0) {
            Py_DECREF(placeholder_list);
            continue;
        }
        if (adjust_placeholders(key, placeholder_list) == -1) {
            Py_DECREF(placeholder_list);
            Py_DECREF(items);
            Py_DECREF(result);
            return -1;
        }
        if (PyDict_SetItem(result, key, placeholder_list) == -1) {
            Py_DECREF(placeholder_list);
            Py_DECREF(items);
            Py_DECREF(result);
            return -1;
        }
        Py_DECREF(placeholder_list);
    }

    Py_DECREF(items);
    *out_placeholders = result;
    return 1;
}

static PyObject *
substitute_value(PyObject *template, PyObject *mapping, PyObject *names)
{
    if (!PyUnicode_Check(template)) {
        PyErr_SetString(PyExc_TypeError, "template must be str");
        return NULL;
    }

    Py_ssize_t nlen = PyList_Check(names) ? PyList_GET_SIZE(names) : 0;
    if (nlen == 1) {
        PyObject *name = PyList_GET_ITEM(names, 0);
        if (PyUnicode_Check(name)) {
            if (PyUnicode_READY(template) == -1) {
                return NULL;
            }
            Py_ssize_t tlen = PyUnicode_GET_LENGTH(template);
            if (tlen >= 3) {
                int kind = PyUnicode_KIND(template);
                void *data = PyUnicode_DATA(template);
                Py_UCS4 first = PyUnicode_READ(kind, data, 0);
                Py_UCS4 second = PyUnicode_READ(kind, data, 1);
                Py_UCS4 last = PyUnicode_READ(kind, data, tlen - 1);
                if (first == '$' && second == '{' && last == '}') {
                    PyObject *value = PyObject_GetItem(mapping, name);
                    return value;
                }
            }
        }
    }

    PyObject *dollar = PyUnicode_FromString("$");
    PyObject *empty = PyUnicode_New(0, 0);
    if (!dollar || !empty) {
        Py_XDECREF(dollar);
        Py_XDECREF(empty);
        return NULL;
    }

    PyObject *format_str = PyUnicode_Replace(template, dollar, empty, -1);
    Py_DECREF(dollar);
    Py_DECREF(empty);
    if (!format_str) {
        return NULL;
    }

    PyObject *result = PyObject_CallMethod(format_str, "format_map", "O", mapping);
    Py_DECREF(format_str);
    return result;
}

/* fallback interpolate: return 0 to signal Python path */
static int
FlatDictCore_interpolate(PyObject *self, int use_variable, int unsafe_eval)
{
    if (!PyMapping_Check(self)) {
        return 0;
    }

    PyObject *placeholders = NULL;
    int collected = collect_placeholders(self, &placeholders);
    if (collected <= 0) {
        return collected;
    }

    if (PyDict_Size(placeholders) == 0) {
        Py_DECREF(placeholders);
        return 1;
    }

    if (ensure_placeholder_helpers() == -1) {
        Py_DECREF(placeholders);
        return -1;
    }

    PyObject *cycle = PyObject_CallFunctionObjArgs(find_circular_reference_fn, placeholders, NULL);
    if (!cycle) {
        Py_DECREF(placeholders);
        return -1;
    }
    if (cycle != Py_None) {
        PyObject *arrow = PyUnicode_FromString("->");
        PyObject *joined = arrow ? PyUnicode_Join(arrow, cycle) : NULL;
        Py_XDECREF(arrow);
        Py_DECREF(cycle);
        Py_DECREF(placeholders);
        if (!joined) {
            return -1;
        }
        PyErr_Format(PyExc_ValueError, "Circular reference found: %U.", joined);
        Py_DECREF(joined);
        return -1;
    }
    Py_DECREF(cycle);

    PyObject *placeholder_names = PySet_New(NULL);
    if (!placeholder_names) {
        Py_DECREF(placeholders);
        return -1;
    }

    Py_ssize_t pos = 0;
    PyObject *k = NULL;
    PyObject *v = NULL;
    while (PyDict_Next(placeholders, &pos, &k, &v)) {
        Py_ssize_t list_len = PyList_GET_SIZE(v);
        for (Py_ssize_t i = 0; i < list_len; ++i) {
            PyObject *name = PyList_GET_ITEM(v, i);
            if (PySet_Add(placeholder_names, name) == -1) {
                Py_DECREF(placeholder_names);
                Py_DECREF(placeholders);
                return -1;
            }
        }
    }

    PyObject *keys = PyDict_Keys(placeholders);
    if (!keys) {
        Py_DECREF(placeholder_names);
        Py_DECREF(placeholders);
        return -1;
    }
    PyObject *keys_set = PySet_New(keys);
    Py_DECREF(keys);
    if (!keys_set) {
        Py_DECREF(placeholder_names);
        Py_DECREF(placeholders);
        return -1;
    }

    PyObject *iter = PyObject_GetIter(placeholder_names);
    if (!iter) {
        Py_DECREF(keys_set);
        Py_DECREF(placeholder_names);
        Py_DECREF(placeholders);
        return -1;
    }

    PyObject *name_obj;
    while ((name_obj = PyIter_Next(iter)) != NULL) {
        int in_keys = PySet_Contains(keys_set, name_obj);
        if (in_keys == -1) {
            Py_DECREF(name_obj);
            Py_DECREF(iter);
            Py_DECREF(keys_set);
            Py_DECREF(placeholder_names);
            Py_DECREF(placeholders);
            return -1;
        }
        if (in_keys == 1) {
            Py_DECREF(name_obj);
            continue;
        }
        PyObject *value = PyObject_GetItem(self, name_obj);
        if (!value) {
            Py_DECREF(name_obj);
            Py_DECREF(iter);
            Py_DECREF(keys_set);
            Py_DECREF(placeholder_names);
            Py_DECREF(placeholders);
            PyObject *repr = PyObject_Repr(self);
            if (!repr) {
                return -1;
            }
            PyErr_Format(PyExc_ValueError, "%U is not found in %U.", name_obj, repr);
            Py_DECREF(repr);
            return -1;
        }
        if (use_variable && ensure_helpers() == 0) {
            int is_var = PyObject_IsInstance(value, VariableType);
            if (is_var == 0) {
                PyObject *wrapped = PyObject_CallFunctionObjArgs(VariableClass, value, NULL);
                if (!wrapped) {
                    Py_DECREF(value);
                    Py_DECREF(name_obj);
                    Py_DECREF(iter);
                    Py_DECREF(keys_set);
                    Py_DECREF(placeholder_names);
                    Py_DECREF(placeholders);
                    return -1;
                }
                if (PyObject_SetItem(self, name_obj, wrapped) == -1) {
                    Py_DECREF(wrapped);
                    Py_DECREF(value);
                    Py_DECREF(name_obj);
                    Py_DECREF(iter);
                    Py_DECREF(keys_set);
                    Py_DECREF(placeholder_names);
                    Py_DECREF(placeholders);
                    return -1;
                }
                Py_DECREF(wrapped);
            } else if (is_var == -1) {
                Py_DECREF(value);
                Py_DECREF(name_obj);
                Py_DECREF(iter);
                Py_DECREF(keys_set);
                Py_DECREF(placeholder_names);
                Py_DECREF(placeholders);
                return -1;
            }
        }
        Py_DECREF(value);
        Py_DECREF(name_obj);
    }
    Py_DECREF(iter);
    Py_DECREF(keys_set);
    Py_DECREF(placeholder_names);

    pos = 0;
    while (PyDict_Next(placeholders, &pos, &k, &v)) {
        PyObject *current = PyObject_GetItem(self, k);
        if (!current) {
            Py_DECREF(placeholders);
            return -1;
        }
        if (!PyUnicode_Check(current)) {
            Py_DECREF(current);
            Py_DECREF(placeholders);
            return 0; /* fallback for unexpected type */
        }
        PyObject *replacement = substitute_value(current, self, v);
        Py_DECREF(current);
        if (!replacement) {
            Py_DECREF(placeholders);
            return -1;
        }
        if (PyObject_SetItem(self, k, replacement) == -1) {
            Py_DECREF(replacement);
            Py_DECREF(placeholders);
            return -1;
        }
        if (unsafe_eval && PyUnicode_Check(replacement)) {
            PyObject *builtins = PyEval_GetBuiltins();
            PyObject *eval_fn = builtins ? PyDict_GetItemString(builtins, "eval") : NULL;
            if (eval_fn) {
                Py_INCREF(eval_fn);
                PyObject *evaluated = PyObject_CallFunctionObjArgs(eval_fn, replacement, NULL);
                Py_DECREF(eval_fn);
                if (evaluated) {
                    if (PyObject_SetItem(self, k, evaluated) == -1) {
                        Py_DECREF(evaluated);
                        Py_DECREF(replacement);
                        Py_DECREF(placeholders);
                        return -1;
                    }
                    Py_DECREF(evaluated);
                } else if (PyErr_ExceptionMatches(PyExc_SyntaxError)) {
                    PyErr_Clear();
                } else {
                    Py_DECREF(replacement);
                    Py_DECREF(placeholders);
                    return -1;
                }
            }
        }
        Py_DECREF(replacement);
    }

    Py_DECREF(placeholders);
    return 1;
}

static int
deep_merge(PyObject *dest, PyObject *src, int overwrite)
{
    if (!PyMapping_Check(src) || !PyMapping_Check(dest)) {
        return 0;
    }
    PyObject *items = PyMapping_Items(src);
    if (!items) return -1;
    Py_ssize_t len = PyList_GET_SIZE(items);
    for (Py_ssize_t i = 0; i < len; ++i) {
        PyObject *item = PyList_GET_ITEM(items, i); /* borrowed */
        PyObject *key = PyTuple_GET_ITEM(item, 0);
        PyObject *value = PyTuple_GET_ITEM(item, 1);
        PyObject *existing = PyObject_GetItem(dest, key);
        if (existing) {
            int both_mapping = PyMapping_Check(existing) && PyMapping_Check(value);
            if (both_mapping) {
                int res = deep_merge(existing, value, overwrite);
                Py_DECREF(existing);
                if (res == -1) {
                    Py_DECREF(items);
                    return -1;
                }
                continue;
            }
            Py_DECREF(existing);
        } else if (PyErr_Occurred()) {
            Py_DECREF(items);
            return -1;
        }
        if (overwrite || !existing) {
            if (PyObject_SetItem(dest, key, value) == -1) {
                Py_DECREF(items);
                return -1;
            }
        }
    }
    Py_DECREF(items);
    return 1;
}

static PyObject *
FlatDictCore_merge(PyObject *self, PyObject *other, int overwrite)
{
    if (!PyMapping_Check(other)) {
        Py_RETURN_FALSE;
    }
    int res = deep_merge(self, other, overwrite);
    if (res == 1) Py_RETURN_TRUE;
    if (res == 0) Py_RETURN_FALSE;
    return NULL;
}

static PyObject *
FlatDictCore_intersect(PyObject *self, PyObject *other)
{
    if (!PyMapping_Check(other) || !PyMapping_Check(self)) {
        Py_RETURN_NONE;
    }
    PyObject *result = PyDict_New();
    if (!result) return NULL;

    PyObject *items = PyMapping_Items(other);
    if (!items) {
        Py_DECREF(result);
        return NULL;
    }
    Py_ssize_t len = PyList_GET_SIZE(items);
    for (Py_ssize_t i = 0; i < len; ++i) {
        PyObject *item = PyList_GET_ITEM(items, i); /* borrowed */
        PyObject *key = PyTuple_GET_ITEM(item, 0);
        PyObject *value = PyTuple_GET_ITEM(item, 1);
        PyObject *existing = PyObject_GetItem(self, key);
        if (!existing) {
            if (PyErr_Occurred()) {
                Py_DECREF(items);
                Py_DECREF(result);
                return NULL;
            }
            continue;
        }
        int eq = PyObject_RichCompareBool(existing, value, Py_EQ);
        Py_DECREF(existing);
        if (eq == 1) {
            if (PyDict_SetItem(result, key, value) == -1) {
                Py_DECREF(items);
                Py_DECREF(result);
                return NULL;
            }
        } else if (eq == -1) {
            Py_DECREF(items);
            Py_DECREF(result);
            return NULL;
        }
    }
    Py_DECREF(items);
    return result;
}

static PyObject *
FlatDictCore_difference(PyObject *self, PyObject *other)
{
    if (!PyMapping_Check(other) || !PyMapping_Check(self)) {
        Py_RETURN_NONE;
    }
    PyObject *result = PyDict_New();
    if (!result) return NULL;

    PyObject *items = PyMapping_Items(other);
    if (!items) {
        Py_DECREF(result);
        return NULL;
    }
    Py_ssize_t len = PyList_GET_SIZE(items);
    for (Py_ssize_t i = 0; i < len; ++i) {
        PyObject *item = PyList_GET_ITEM(items, i); /* borrowed */
        PyObject *key = PyTuple_GET_ITEM(item, 0);
        PyObject *value = PyTuple_GET_ITEM(item, 1);
        PyObject *existing = PyObject_GetItem(self, key);
        if (existing) {
            int eq = PyObject_RichCompareBool(existing, value, Py_EQ);
            Py_DECREF(existing);
            if (eq == -1) {
                Py_DECREF(items);
                Py_DECREF(result);
                return NULL;
            }
            if (eq == 1) {
                continue;
            }
        } else if (PyErr_Occurred()) {
            Py_DECREF(items);
            Py_DECREF(result);
            return NULL;
        }
        if (PyDict_SetItem(result, key, value) == -1) {
            Py_DECREF(items);
            Py_DECREF(result);
            return NULL;
        }
    }
    Py_DECREF(items);
    return result;
}

static PyObject *
FlatDictCore_reduce(PyObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *cls = PyObject_GetAttrString(self, "__class__");
    if (!cls) {
        return NULL;
    }
    PyObject *data = PyDict_Copy(self);
    if (!data) {
        Py_DECREF(cls);
        return NULL;
    }
    PyObject *args = PyTuple_Pack(1, data);
    if (!args) {
        Py_DECREF(cls);
        Py_DECREF(data);
        return NULL;
    }
    PyObject *attrs = PyObject_GetAttrString(self, "__dict__");
    if (!attrs) {
        PyErr_Clear();
        attrs = Py_None;
        Py_INCREF(Py_None);
    }
    PyObject *result = PyTuple_Pack(3, cls, args, attrs);
    Py_DECREF(attrs);
    Py_DECREF(cls);
    Py_DECREF(data);
    Py_DECREF(args);
    return result;
}

static PyMethodDef FlatDictCore_methods[] = {
    {"__reduce__", (PyCFunction)FlatDictCore_reduce, METH_NOARGS, "Pickle support."},
    {NULL, NULL, 0, NULL}};

static PyObject *
py_flatdict_interpolate(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *mapping = NULL;
    int use_variable = 1;
    int unsafe_eval = 0;
    static char *kwlist[] = {"mapping", "use_variable", "unsafe_eval", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|pp:flatdict_interpolate", kwlist, &mapping, &use_variable,
                                    &unsafe_eval)) {
        return NULL;
    }
    int res = FlatDictCore_interpolate(mapping, use_variable, unsafe_eval);
    if (res == -1) return NULL;
    if (res == 0) Py_RETURN_FALSE;
    Py_RETURN_TRUE;
}

static PyObject *
py_flatdict_merge(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *mapping = NULL;
    int overwrite = 1;
    static char *kwlist[] = {"mapping", "overwrite", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|p:flatdict_merge", kwlist, &mapping, &overwrite)) {
        return NULL;
    }
    return FlatDictCore_merge(self, mapping, overwrite);
}

static PyObject *
py_flatdict_intersect(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *mapping = NULL;
    static char *kwlist[] = {"mapping", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O:flatdict_intersect", kwlist, &mapping)) {
        return NULL;
    }
    return FlatDictCore_intersect(self, mapping);
}

static PyObject *
py_flatdict_difference(PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *mapping = NULL;
    static char *kwlist[] = {"mapping", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O:flatdict_difference", kwlist, &mapping)) {
        return NULL;
    }
    return FlatDictCore_difference(self, mapping);
}

static PyTypeObject FlatDictCoreType = {
    PyVarObject_HEAD_INIT(NULL, 0).tp_name = "chanfig._cext.FlatDictCore",
    .tp_basicsize = sizeof(FlatDictCore),
    .tp_itemsize = 0,
    .tp_base = NULL, /* filled in module init */
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_getattro = FlatDictCore_getattro,
    .tp_setattro = FlatDictCore_setattro,
    .tp_as_mapping = &(PyMappingMethods){
        .mp_length = 0,
        .mp_subscript = FlatDictCore_subscript,
        .mp_ass_subscript = FlatDictCore_ass_subscript,
    },
    .tp_methods = FlatDictCore_methods,
};

static struct PyModuleDef chanfigmodule = {
    PyModuleDef_HEAD_INIT,
    "_cext",
    "CHANfiG C extension helpers.",
    -1,
    ChanfigMethods};

PyMODINIT_FUNC
PyInit__cext(void)
{
    PyObject *m = PyModule_Create(&chanfigmodule);
    if (m == NULL) {
        return NULL;
    }

    /* init FlatDictCore */
    FlatDictCoreType.tp_base = &PyDict_Type;
    if (PyType_Ready(&FlatDictCoreType) < 0) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(&FlatDictCoreType);
    if (PyModule_AddObject(m, "FlatDictCore", (PyObject *)&FlatDictCoreType) < 0) {
        Py_DECREF(&FlatDictCoreType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
static PyMethodDef ChanfigMethods[] = {
    {"find_placeholders", (PyCFunction)py_find_placeholders, METH_VARARGS | METH_KEYWORDS,
     "find_placeholders(text: str) -> list[str]\n"
     "Find placeholders in the form ${...}, including nested ones."},
    {"flatdict_interpolate", (PyCFunction)py_flatdict_interpolate, METH_VARARGS | METH_KEYWORDS,
     "flatdict_interpolate(mapping, use_variable=True, unsafe_eval=False) -> bool\n"
     "Attempt fast interpolation on FlatDict-like mapping. Returns True if handled, False to fallback."},
    {"flatdict_merge", (PyCFunction)py_flatdict_merge, METH_VARARGS | METH_KEYWORDS,
     "flatdict_merge(mapping, overwrite=True) -> bool\n"
     "Shallow merge helper; returns True if handled, False to fall back to Python for complex cases."},
    {"flatdict_intersect", (PyCFunction)py_flatdict_intersect, METH_VARARGS | METH_KEYWORDS,
     "flatdict_intersect(mapping) -> dict | None\n"
     "Shallow intersect helper; returns a dict of matching items, or None to signal fallback."},
    {"flatdict_difference", (PyCFunction)py_flatdict_difference, METH_VARARGS | METH_KEYWORDS,
     "flatdict_difference(mapping) -> dict | None\n"
     "Shallow difference helper; returns a dict of differing items, or None to signal fallback."},
    {NULL, NULL, 0, NULL}};
