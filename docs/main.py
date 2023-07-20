# Debut copie
import hashlib
import os
import random
import re
from math import log10
from typing import Literal, Union
from urllib.parse import unquote

MAX_EMPTY_IDE = 10**8
# Fin copie


def define_env(env):
    "Hook function"

    @env.macro
    def script(lang: str, nom: str) -> str:
        "Renvoie le script dans une balise bloc avec langage spécifié"
        return (
            f"""```{lang}
--8<---  "docs/"""
            + os.path.dirname(env.variables.page.url.rstrip("/"))
            + f"""/{nom}"
```"""
        )

    # f"docs/{os.path.dirname(env.variables.page.url.rstrip('/'))}/scripts/{nom}.py"

    @env.macro
    def py(nom: str) -> str:
        return script("python", "scripts/" + nom + ".py")

    @env.macro
    def html_fig(num: int) -> str:
        "Renvoie le code HTML de la figure n° `num`"
        return f'--8<-- "docs/' + os.path.dirname(env.variables.page.url.rstrip("/")) + f'/figures/fig_{num}.html"'

    env.variables["compteur_exo"] = 0

    @env.macro
    def exercice(var: bool = True, prem: Union[int, None] = None) -> str:
        # si var == False, alors l'exercice est placé dans une superfence.
        if prem is not None:
            env.variables["compteur_exo"] = prem
        env.variables["compteur_exo"] += 1
        root = f"Exercice { env.variables['compteur_exo']}"
        return f"""exo \"{root}\"""" if var else '"' + root + '"'

    @env.macro
    def cours() -> str:
        return f'success "Cours"'

    @env.macro
    def ext() -> str:
        return f'ext "Pour aller plus loin"'

    @env.macro
    def tit(ch: str = "", text: str = "") -> str:
        # Tasklist In Table
        checked = 'checked=""' if ch == "x" else ""
        return f"""<ul class="task-list"><li class="task-list-item">\
            <label class="task-list-control"><input type="checkbox" {checked}>\
            <span class="task-list-indicator"></span>\
            </label>{text}</li></ul>"""

    # Debut copie
    env.variables["term_counter"] = 0
    env.variables["IDE_counter"] = 0
    INFINITY_SYMBOL = "∞"

    @env.macro
    def terminal() -> str:
        """
        @brief : Create a Python Terminal.
        @details : Two layers to avoid focusing on the Terminal. 1) Fake Terminal using CSS 2) A click hides the fake
        terminal and triggers the actual Terminal.
        """
        id_ide = env.variables["term_counter"]
        env.variables["term_counter"] += 1
        return f"""<div onclick='start_term("id{id_ide}")' id="fake_id{id_ide}" class="py_mk_terminal_f"><label class="terminal"><span>>>> </span></label></div><div id="id{id_ide}" class="py_mk_hide"></div>"""

    def read_external_file(script_name: str, path: str, extension: str = "py") -> str:
        """
        @brief : Read a Python file that is uploaded on the server.
        @details : The content of the file is hidden in the webpage. Replacing \n, _ and * by a string enables
        the integration in mkdocs admonitions.
        """
        docs_path = "docs/docs/"

        try:
            relative_path = "scripts" if path == "" else path
            with open(os.path.join(docs_path, relative_path, f"{script_name}.{extension}")) as filename:
                content = "".join(filename.readlines())
                content = content + "\n"

            return escape_problematic_characters(content)
        except FileNotFoundError:
            return ""

    def escape_problematic_characters(script: str) -> str:
        return script.replace("\n", "bksl-nl").replace("_", "py-und").replace("*", "py-str")

    def get_image_path() -> str:
        split_page_url = os.path.dirname(convert_url_to_utf8(env.variables.page.url)).split("/")
        prefix = "".join(["../" for folder in split_page_url if folder != ""])
        return f"""{prefix}pyodide-mkdocs"""

    # TODO : this issue concerning the urls must be closed ASAP
    def get_filepath() -> str:
        print("docs_dirs", env.conf["docs_dir"])
        print(
            "P1",
            env.variables.page.abs_url,
            "/".join(
                filter(
                    lambda folder: folder != "",
                    convert_url_to_utf8(env.variables.page.url).split("/")[:-2],
                )
            ),
        )
        print(
            "P2",
            env.variables.page.abs_url,
            "/".join(
                filter(
                    lambda folder: folder != "",
                    convert_url_to_utf8(env.variables.page.abs_url).split("/")[2:-2],
                )
            ),
        )
        return "/".join(
            filter(
                lambda folder: folder != "",
                convert_url_to_utf8(env.variables.page.abs_url).split("/")[2:-2],
            )
        )

    # TODO : handle the case where the same files are loaded on the same page.
    def generate_id_ide(content: str) -> str:
        """
        @brief : Return current number IDE {id_ide}.
        """
        if content not in [None, ""]:
            id_ide = hashlib.sha1(content.encode("utf-8")).hexdigest()
        else:  # non-existent file, empty file
            id_ide = env.variables["IDE_counter"]
            env.variables["IDE_counter"] += 1
        return str(id_ide).zfill(int(log10(MAX_EMPTY_IDE)))

    def blank_space(s: float = 0.3) -> str:
        """
        @brief : Return 5em blank spaces. Use to spread the buttons evenly
        """
        return f"""<span style="display: inline-block; width:{s}em"></span>"""

    def format_unlimited_attempts(max: Union[int, Literal["+"]]) -> Union[int, Literal["∞"]]:
        return int(max) if max not in ["+", 1000] else INFINITY_SYMBOL

    def get_max_from_file(content: str) -> str:
        """
        @brief : Allows to specify max number of attempt on first line of input file with #MAX=6
        """
        split_content = content.split("bksl-nl")
        first_line = split_content[0]
        if first_line[:4] != "#MAX":
            return ""

        used_max = first_line.split("=")[1].strip()
        return used_max

    def strip_empty_lines_after_max(content: str) -> str:
        split_content = content.split("bksl-nl")
        i = 1
        while split_content[i] == "":
            i += 1
        content = "bksl-nl".join(split_content[i:])
        return content

    def get_allowed_number_of_attempts(
        max_from_file: str, max_IDE: Union[int, Literal["+"]]
    ) -> Union[int, Literal["∞"]]:
        if max_from_file != "":
            return format_unlimited_attempts(int(max_from_file) if max_from_file != "+" else "+")

        return format_unlimited_attempts(max_IDE)

    def test_style(script_name: str, element: str) -> bool:
        quotes = ["'", '"']
        ide_style = ["", "v"]
        styles = [f"""IDE{style}({quote}{script_name}{quote}""" for quote in quotes for style in ide_style]
        return any([style for style in styles if style in element])

    def convert_url_to_utf8(nom: str) -> str:
        return unquote(nom, encoding="utf-8")

    @env.macro
    def IDEv(script_name: str = "", MAX: Union[int, Literal["+"]] = 5, SANS: str = "") -> str:
        """
        @brief : Helper macro to generate vertical IDE in Markdown mkdocs.
        @details : Starts the IDE function with 'v' mode.
        """
        return IDE(script_name, mode="_v", MAX=MAX, SANS=SANS)

    def generate_key(filepath: str):
        try:
            with open(f"docs/{filepath}/clef.txt", "r", encoding="utf8") as filename:
                key_ide = filename.read()
        except FileNotFoundError:
            key_ide = ""  # base case -> no clef.txt file
        return key_ide

    @env.macro
    def create_button(button_name: str, onclick_action: str, isTranslated: bool = False) -> str:
        # AVAILABLE_BUTTONS = {
        #     "Play": "Lancer",
        #     "Download": "Télécharger",
        #     "Check": "Valider",
        #     "Restart": "Recharger",
        #     "Save": "Sauvegarder",
        #     "Upload": "Téléverser",
        # }

        # def define_action(*args: tuple[str, ...]) -> str:
        #     options = '","'.join([f"{arg}" for arg in args[0]])
        #     return f"""\'{button_name}("{options}")\'"""

        tooltip_text = button_name

        return f"""<button class="tooltip" onclick={onclick_action}>\
            <img src="{get_image_path()}/icons8-{button_name.lower()}-64.png">\
            <span class="tooltiptext">{tooltip_text}</span>\
            </button>"""

    def create_upload_button(editor_name: str) -> str:
        """
        @brief : Create upload button for a IDE number {id_ide}.
        @details : Use an HTML input to upload a file from user. The user clicks on the button to fire a JS event
        that triggers the hidden input.
        """
        onclick_action = f""""document.getElementById('input_{editor_name}').click()" """
        return f"""{create_button("Upload", onclick_action)}\
                <input type="file" id="input_{editor_name}" name="file" enctype="multipart/form-data" class="py_mk_hide"/>"""

    def create_unittest_button(
        editor_name: str,
        script_name: str,
        path: str,
        mode: str,
        number_max_attempts: Union[Literal["∞"], int],
    ) -> str:
        """
        @brief : Generate the button for IDE {id_ide} to perform the unit tests if a valid test_script.py is present.
        @details : Hide the content in a div that is called in the Javascript
        """
        stripped_script_name = script_name.split("/")[-1]
        relative_path = "/".join(script_name.split("/")[:-1])
        script_name = f"{relative_path}/{stripped_script_name}_test"
        content = read_external_file(script_name, path)

        if content == "":
            return ""

        onclick_action = f"""\'check("{editor_name}","{mode}")\'"""
        return f"""<span id="test_term_{editor_name}" class="py_mk_hide">{content}</span>\
            {create_button("Check", onclick_action)}\
            <span class="compteur">{number_max_attempts}/{number_max_attempts}</span>"""

    def div(content: str, div_options: dict[str, str]) -> str:
        formatted_div_options = " ".join(
            [f"""{div_attribute}="{attribute_value}" """ for div_attribute, attribute_value in div_options.items()]
        )
        return f"""<div {formatted_div_options}>{content}</div>"""

    def grouped_buttons(buttons: str) -> str:
        return buttons + blank_space(1)

    def generate_empty_ide(editor_name: str, mode: str) -> str:
        shortcut_comment_asserts = f'<span id="comment_{editor_name}" class="comment">###</span>'

        div_editor_terminal = div("", {"id": f"term_{editor_name}", "class": f"term_editor{mode}"})

        div_decorations = (
            f'<div class="line_v"><div id="{editor_name}"></div></div>'
            if mode == "_v"
            else f'<div class="line" id="{editor_name}"></div>'
        )

        return div(
            f"{shortcut_comment_asserts}{div_decorations}{div_editor_terminal}",
            {"class": f"wrapper{mode}"},
        )

    def generate_row_of_buttons(
        editor_name: str,
        script_name: str,
        mode: str,
        filepath: str,
        number_max_attempts: Union[int, Literal["∞"]],
    ) -> str:
        play_buttons_group = grouped_buttons(
            create_button("Play", f"""'play("{editor_name}","{mode}")'""")
            + create_unittest_button(editor_name, script_name, filepath, mode, number_max_attempts)
        )

        transfer_buttons_group = grouped_buttons(
            create_button("Download", f"""\'download("{editor_name}","{script_name}")\'""")
            + blank_space()
            + create_upload_button(editor_name)
        )

        save_buttons_group = grouped_buttons(
            create_button("Restart", f"""\'restart("{editor_name}")\'""")
            + blank_space()
            + create_button("Save", f"""\'save("{editor_name}")\'""")
        )

        return play_buttons_group + transfer_buttons_group + save_buttons_group

    def get_last_dir_from(path: str) -> str:
        return path.split("/")[-2]

    def get_custom_dir() -> Union[str, None]:
        for path in env.conf["theme"].dirs:
            if os.path.exists(path + "/pyodide-mkdocs/start_REM.md"):
                return get_last_dir_from(path)
        return None

    @env.macro
    def insert_remark_file(script_name: str, key_ide: str) -> str:
        IDE_calls_from_md_file = [elt for elt in env.page.markdown.split("\n") if test_style(script_name, elt)]
        first_IDE_call = IDE_calls_from_md_file[0] if len(IDE_calls_from_md_file) >= 1 else ""

        leading_spaces = " " * (len(first_IDE_call) - len(first_IDE_call.lstrip()))

        block_remark = ""
        if script_name != "":
            block_remark = f"""
{leading_spaces}--8<--- "{get_custom_dir()}/pyodide-mkdocs/start_REM.md"
"""
            filepath = get_filepath()
            block_remark += (
                f'''
{leading_spaces}--8<--- "docs/{filepath if filepath != "" else "scripts"}/{script_name}_REM.md"'''
                if key_ide == ""
                else f""
            )

            block_remark += f"""
{leading_spaces}--8<--- "{get_custom_dir()}/pyodide-mkdocs/end_REM.md"
"""
        return block_remark

    def insert_content(editor_name: str, ide_content: str) -> str:
        return f"""<span id="content_{editor_name}" class="py_mk_hide">{ide_content}</span>"""

    def insert_corr_content(editor_name: str, ide_corr_content: str, key_ide: str) -> str:
        return f"""<span id="corr_content_{editor_name}" class="py_mk_hide" data-strudel="{str(key_ide)}">{ide_corr_content}</span>"""

    @env.macro
    def IDE(
        script_name: str = "",
        mode: str = "",
        MAX: Union[int, Literal["+"]] = 5,
        SANS: str = "",
        SIZE: int = 30,
    ) -> str:
        """
        @brief : Create an IDE (Editor+Terminal) within an Mkdocs document. {script_name}.py is loaded on the editor if present.
        @details : Two modes are available : vertical or horizontal. Buttons are added through functional calls.
        Last span hides the code content of the IDE when loaded.
        """
        filepath = get_filepath()

        ide_content = read_external_file(script_name, filepath)
        id_ide = generate_id_ide(ide_content)

        if (max_from_file := get_max_from_file(ide_content)) != "":
            ide_content = strip_empty_lines_after_max(ide_content)
        allowed_number_of_attempts = get_allowed_number_of_attempts(max_from_file, MAX)

        format_excluded_instructions = (
            lambda instructions: "," + "".join(instructions.split(" ")) if len(instructions) > 0 else ""
        )
        editor_name = f"editor_{id_ide}"

        div_exercise = div(
            generate_empty_ide(editor_name, mode)
            + generate_row_of_buttons(editor_name, script_name, mode, filepath, allowed_number_of_attempts),
            {
                "class": "py_mk_ide",
                "data-max": f"{allowed_number_of_attempts}",
                "data-max_size": f"{SIZE}",
                "data-exclude": f'{"eval,exec" + format_excluded_instructions(SANS)}',
            },
        )

        div_exercise += insert_content(editor_name, ide_content)

        key_ide = generate_key(filepath)
        ide_corr_content = read_external_file(
            f"""{'/'.join(script_name.split('/')[:-1])}/{script_name.split('/')[-1]}_corr""",
            filepath,
        )
        div_exercise += insert_corr_content(editor_name, ide_corr_content, key_ide)
        div_exercise += insert_remark_file(script_name, key_ide)

        return div_exercise

    @env.macro
    def mult_col(*text):
        cmd = """<table style="border-color:transparent;background-color:transparent"><tr>"""
        for column in text:
            cmd += f"""<td><b style="font-size:1.2em">{column}</td>"""
        cmd += f"""</tr></table>"""
        return cmd

    def generate_id():
        alphabet = [chr(ord("a") + i) for i in range(26)]
        return "".join(random.choices(alphabet, k=6))

    def latexify(answer):
        """$ might not be the first character :
        blabla $1+1$
        """
        answer = str(answer)
        if answer.count("$") - answer.count("\$") >= 2:  # regex begin ___$ and end $____ and $ not preceded by \
            string = ""
            start_dollar = True
            for i in range(len(answer)):
                lettre = answer[i]
                if lettre == "$":
                    if i == 0 or (i >= 1 and answer[i - 1] != "\\"):  # case escaping dollar \$
                        string += "\(" if start_dollar else "\)"
                        start_dollar = not start_dollar
                    else:
                        string += "$"
                else:
                    string += lettre
            return string
        return answer

    @env.macro
    def qcm(list_answers, list_correct, opts=None, shuffle=True, single=True):
        # single -> une seule question de QCM
        print("opts", opts)
        if type(list_correct) == int:
            list_correct = [list_correct]
        print("liste", list_correct, type(list_correct))
        list_correct = list(map(lambda x: x - 1, list_correct))  # back to 0 to n-1 indexing

        def spanify(html_tag):
            return f"""<span>{html_tag}</span>"""

        def buttonify(answer, id, correct):
            reveal = "reveal" if single else ""
            return f"""<input type="checkbox" id="{id}" class="qcm-checkbox {correct} {reveal}"><span class="check-toggle"></span><label for="{id}" class="qcm-item arithmatex">{answer}</label>"""

        def codeblockify(answer):
            if answer[0:3] == "`#!":
                sep = answer.index(" ")
                language = answer[3:sep]
                return f"""<pre style="display: inline;"><code style="display: inline;" class="language-{language} qcm">{answer[sep:-1]}</code></pre>"""
            return answer

        indices = [i for i in range(len(list_answers))]
        # if shuffle: random.shuffle(indices)

        dict_correspondance = {indices[i]: i for i in range(len(list_answers))}
        inv_dict_correspondance = {i: indices[i] for i in range(len(list_answers))}

        id = generate_id()

        prefix = "data-var-"
        variable_part = ""
        if opts != None:
            print("opts", opts, type(opts))
            for clé in opts:
                variable_part += f"""{prefix}{clé} = "{opts[clé]}" """
        html_element = f"""<div class="wrapper_qcm" id = "qcm_{id}" data-n-correct = {len(list_correct)} data-shuffle = {1 if shuffle else 0} {variable_part}>"""

        for i in range(len(list_answers)):
            answer = list_answers[inv_dict_correspondance[i]]
            if type(answer) != str:
                try:
                    answer = str(answer)
                except:
                    answer = "Erreur de format"
            answer = codeblockify(latexify(answer))
            id_answer = f"""{id}-{i}"""
            correct_answer = "correct" if inv_dict_correspondance[i] in list_correct else "incorrect"
            html_element += f"""{spanify(buttonify(answer, id_answer, correct_answer))}"""
        html_element += "</div>"

        return html_element

    def extract_csv_file(input_file, sep=";"):
        # extract info from external file
        docs_path = f"""docs/"""
        path = "/".join(
            filter(
                lambda folder: folder != "",
                convert_url_to_utf8(env.variables.page.abs_url).split("/")[2:-2],
            )
        )

        try:
            if path == "":
                f = open(f"""{docs_path}/scripts/{input_file}""")
            else:
                f = open(f"""{docs_path}/{path}/{input_file}""")

            content = list(map(lambda x: x[:-1], f.readlines()))
            header = content.pop(0).split(sep)
            csv_file = []
            print(header)
            for ligne in content:
                split_ligne = ligne.split(sep)
                dico = {
                    header[i]: split_ligne[i].replace("\\\\", "\\") if split_ligne[i] != "" else None
                    for i in range(len(header))
                }
                csv_file.append(dico)

            f.close()
            return csv_file
        except:
            return ""

    def get_variables_state(string, sep="{}"):
        var_pos = {}
        for inter in re.finditer(rf"{sep[0]}\w+{sep[1]}", string):
            # print(inter.start(), inter.end(), inter.group(0)[1:-1])
            if var_name := inter.group(0)[1:-1] not in var_pos:
                var_pos[var_name] = [inter.span()]
            else:
                var_pos[var_name].append(inter.span())
        return var_pos

    @env.macro
    def multi_qcm(*input, shuffle=True):
        def latexify(answer):
            if answer.count("$") - answer.count("\$") >= 2:  # regex begin ___$ and end $____ and $ not preceded by \
                string = ""
                start_dollar = True
                for i in range(len(answer)):
                    lettre = answer[i]
                    if lettre == "$":
                        if i == 0 or (i >= 1 and answer[i - 1] != "\\"):  # case escaping dollar \$
                            string += "\(" if start_dollar else "\)"
                            start_dollar = not start_dollar
                        else:
                            string += "$"
                    else:
                        string += lettre
                return string
            return answer

        def convert_type(string):
            string = string.strip()
            if string[0] in ["'", '"', "‘", "“"]:
                return str(string[1:-1])
            elif "." in string:
                return float(string)
            else:
                return int(string)

        def dictionnarify(string):
            string = string + ","
            dico = {}
            regex = r"\s*(\w*)\s*:\s*(\[[\s\w,\.'\"‘“’”]*\]|\w*)\s*,"
            words = re.findall(regex, string)
            for var in words:
                dico[var[0]] = list(map(convert_type, var[1].strip("[").strip("]").split(",")))
            return dico

        liste_QCM = []
        if type(input[0]) == str:
            csv_file = extract_csv_file(input[0])
            for entry in csv_file:
                question = entry["Question"]
                list_answers = [entry[clé] for clé in entry if "Answer" in clé and entry[clé] != None]
                list_correct = list(map(int, entry["Valid"].split(",")))
                dictionnaire_var = dictionnarify(entry["Variable"]) if entry["Variable"] != None else None
                liste_QCM.append([question, list_answers, list_correct, dictionnaire_var])
        else:
            for i in range(len(input)):
                question = input[i][0]
                list_answers = input[i][1]
                list_correct = input[i][2]
                dictionnaire_var = input[i][3] if len(input[i]) == 4 else None
                liste_QCM.append([question, list_answers, list_correct, dictionnaire_var])

        id_qcm = generate_id()
        html_element = "<div>"
        for i, entry in enumerate(liste_QCM):
            question = entry[0]
            list_answers = entry[1]
            list_correct = entry[2]
            dictionnaire_var = entry[3]

            print(entry, dictionnaire_var)

            html_element += f"<div class = 'setQCM'>"
            html_element += f"<span class = 'questionQCM arithmatex' data-nq = {i+1}>{latexify(question)}</span>"
            html_element += qcm(
                list_answers,
                list_correct,
                opts=dictionnaire_var,
                shuffle=shuffle,
                single=False,
            )
            html_element += "</div>"
        html_element += f"""<div class="buttonWrapper"><span class = "validationButton" id = "valider_{id_qcm}">Valider</span><span class = "validationButton" id = "recharger_{id_qcm}">Recharger</span></div><div class = "showScore" id="score_{id_qcm}"></div>"""
        html_element += "</div>"
        return html_element

    # Fin copie
