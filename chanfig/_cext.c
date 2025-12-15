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

/* ---------------- FlatDictCore ---------------- */

typedef struct {
    PyDictObject dict;
} FlatDictCore;

/* lazily imported helpers */
static PyObject *VariableType = NULL;
static PyObject *VariableClass = NULL;
static PyObject *get_cached_annotations_fn = NULL;
static PyObject *honor_annotation_fn = NULL;

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
    if (strcmp(name, "getattr") == 0 || strcmp(name, "setattr") == 0 || strcmp(name, "delattr") == 0 ||
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
    {NULL, NULL, 0, NULL}};
