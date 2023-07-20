var debug_mode = false;
var dict = {}; // Global dictionnary tracking the number of clicks
var hdrPlaceholderRe = /#\s*-[\s|-]*HDR\s*-[\s|-]*#/i;
var CURRENT_REVISION = "0.9.1";

function sleep(s) {
  return new Promise((resolve) => setTimeout(resolve, s));
}

/* This function is needed to deal with correct display of tables in tables and Pyodide */
const echo = (term, msg, ...opts) => {
  function keepFirstLetterAfterBrackets(match, ...args) {
    return `&lsqb;&lsqb;${match.slice(2)}`;
  }
  term.echo(
    msg
      .replace(/(\[\[)[^a-z;]/g, keepFirstLetterAfterBrackets)
      .replace(/\]\]/g, "&rsqb;&rsqb;"),
    ...opts
  );
};

async function main() {
  globalThis.pyodide = await loadPyodide();
}

function inputWithPrompt(text) {
  let result = prompt(text);
  $.terminal.active().echo(result);
  return result;
}

let pyodideReadyPromise = main();

async function tryImportFromPyPi(promptLine) {
  let hasImports = promptLine.startsWith("import");
  if (hasImports) {
    try {
      await pyodide.loadPackage("micropip");
      const micropip = pyodide.pyimport("micropip");
      await micropip.install(promptLine.match(/import (\w+)/i)[1]);
    } catch {}
  }
}

async function pyterm(id, height) {
  await pyodideReadyPromise;
  let namespace = pyodide.globals.get("dict")();

  // creates the console
  // the variable pyconsole is created here.
  pyodide.runPython(
    `
    import sys
    from pyodide.ffi import to_js
    from pyodide.console import PyodideConsole, repr_shorten
    import __main__
        
    pyconsole = PyodideConsole(__main__.__dict__)
    
    import builtins

    async def await_fut(fut):
      res = await fut  
      if res is not None:
        builtins._ = res 
      return to_js([res], depth=1)
    
    def clear_console():
      pyconsole.buffer = []
`,
    { globals: namespace }
  );
  let repr_shorten = namespace.get("repr_shorten");
  let await_fut = namespace.get("await_fut");
  let pyconsole = namespace.get("pyconsole");
  let clear_console = namespace.get("clear_console");

  namespace.destroy();

  let ps1 = ">>> ",
    ps2 = "... ";

  async function lock() {
    let resolve;
    let ready = term.ready;
    term.ready = new Promise((res) => (resolve = res));
    await ready;
    return resolve;
  }

  async function interpreter(command, id = null) {
    let unlock = await lock();
    term.pause();
    // multiline should be split (useful when pasting)
    for (let c of command.split("\n")) {
      if (id != null) {
        let exclude = document.getElementById(id.slice(1)).parentElement
          .parentElement.dataset.exclude;
        if (exclude != "" && exclude != undefined) {
          for (let noImports of exclude.split(",")) {
            if (c.includes(noImports)) c = "#" + c;
          }
          console.log(id);
        }
      }

      tryImportFromPyPi(c);

      let fut = pyconsole.push(c);
      term.set_prompt(fut.syntax_check === "incomplete" ? ps2 : ps1);
      switch (fut.syntax_check) {
        case "syntax-error":
          term.error(fut.formatted_error.trimEnd());
          continue;
        case "incomplete":
          continue;
        case "complete":
          break;
        default:
          throw new Error(`Unexpected type ${ty}`);
      }

      // In JavaScript, await automatically also awaits any results of
      // awaits, so if an async function returns a future, it will await
      // the inner future too. This is not what we want so we
      // temporarily put it into a list to protect it.
      let wrapped = await_fut(fut);
      // complete case, get result / error and print it.
      try {
        let [value] = await wrapped;
        if (value !== undefined) {
          echo(
            $.terminal.active(),
            repr_shorten.callKwargs(value, {
              separator: "\n<long output truncated>\n",
            })
          );
        }
        if (pyodide.isPyProxy(value)) {
          value.destroy();
        }
      } catch (e) {
        if (e.constructor.name === "PythonError") {
          const message = fut.formatted_error || e.message;
          term.error(message.trimEnd());
        } else {
          throw e;
        }
      } finally {
        fut.destroy();
        wrapped.destroy();
      }
    }
    term.resume();
    await sleep(10);
    unlock();
  }

  // Code issued from https://stackoverflow.com/questions/5379120/get-the-highlighted-selected-text
  function getSelectionText() {
    var text = "";
    if (window.getSelection) {
      text = window.getSelection().toString();
    } else if (document.selection && document.selection.type != "Control") {
      text = document.selection.createRange().text;
    }
    return text;
  }

  let term = $(id).terminal(
    // creates terminal
    (command) => interpreter(command, id), // how to read the input
    {
      greetings: "", // pyconsole.banner(),
      prompt: ps1,
      completionEscape: false,
      height: height, // if not specified, css says 200
      completion: function (command, callback) {
        // autocompletion
        callback(pyconsole.complete(command).toJs()[0]);
      },
      keymap: {
        "CTRL+C": async function (event, original) {
          if (!getSelectionText()) {
            let p = $.terminal.active().get_command();
            clear_console();
            echo($.terminal.active(), ps1 + p);
            echo($.terminal.active(), error("KeyboardInterrupt"));
            term.set_command("");
            term.set_prompt(ps1);
          }
        },
      },
    }
  );

  window.term = term;
  pyconsole.stdout_callback = (s) =>
    echo($.terminal.active(), s, { newline: false });
  pyconsole.stderr_callback = (s) => {
    $.terminal.active().error(s.trimEnd());
  };

  term.ready = Promise.resolve();
  pyodide._module.on_fatal = async (e) => {
    term.error(
      "Pyodide has suffered a fatal error. Please report this to the Pyodide maintainers."
    );
    term.error("The cause of the fatal error was:");
    term.error(e);
    term.error("Look in the browser console for more details.");
    await term.ready;
    term.pause();
    await sleep(15);
    term.pause();
  };

  pyodide.runPython(
    `
    RECURSION_LIMIT = 100

    def version():
      print("${stress("Pyodide-MkDocs")} : version ${error(CURRENT_REVISION)}")
    
    def getrecursionlimit():
      return RECURSION_LIMIT

    def setrecursionlimit(limit: int):
      RECURSION_LIMIT = min(limit, 200)

    import inspect

    def recursion_limiter(callback):
      def recursion_wrapper(*args, **kwargs):
          if len(inspect.stack()) / 2 > RECURSION_LIMIT:
              raise RecursionError(
                  f"maximum recursion depth exceeded for function {callback.__name__}"
              )

          return callback(*args, **kwargs)
  
      return recursion_wrapper
    
    from js import inputWithPrompt
    input = inputWithPrompt
    __builtins__.input = inputWithPrompt
    `
  );
}

function removeLines(data, moduleName) {
  return data
    .split("\n")
    .filter(
      (sentence) =>
        !(
          sentence.includes("import " + moduleName) ||
          sentence.includes("from " + moduleName)
        )
    )
    .join("\n");
}

// This function should be called for HDR and main code
async function foreignModulesFromImports(
  code,
  moduleDict = {},
  editorName = ""
) {
  await pyodideReadyPromise;

  pyodide.runPython(
    `from pyodide.code import find_imports\nimported_modules = find_imports(${JSON.stringify(
      code
    )})`
  );
  const importedModules = pyodide.globals.get("imported_modules").toJs();
  var executedCode = code;

  // WARNING : there is probably a memory leak here (namespace issue)
  await pyodide.loadPackage("micropip");
  let micropip = pyodide.pyimport("micropip");

  for (let moduleName of importedModules) {
    if (Object.keys(moduleDict).length != 0 && moduleName in moduleDict) {
      var moduleFakeName = moduleDict[moduleName];
      // number of characters before the first occurrence of the module name, presumably the import clause
      var indexModule = executedCode.indexOf(moduleName);
      // substring to count the number of newlines
      var tempString = executedCode.substring(0, indexModule);
      // counting the newlines
      var lineNumber = tempString.split("\n").length;

      let importLine = executedCode.split("\n")[lineNumber - 1]; // getting the import line, now the business starts.

      // taking into consideration the various import options
      // Idea : change the import turtle of a user into import pyo_js_turtle
      // import turtle as tl	>	import js-turtle as tl
      // import turtle		>	import js-turtle as turtle
      // from turtle import *	>	from js-turtle import *
      if (
        importLine.includes("import " + moduleName) &&
        !importLine.includes("as")
      ) {
        importLine = importLine.replace(
          moduleName,
          moduleFakeName + " as " + moduleName
        );
      } else {
        importLine = importLine.replace(moduleName, moduleFakeName);
      }
      if (moduleName.includes("turtle")) showGUI(editorName);

      await micropip.install(moduleFakeName);
      executedCode = `${importLine}\n` + executedCode;
      executedCode = removeLines(executedCode, moduleName);
    } else {
      try {
        await micropip.install(moduleName);
      } catch {}
    }
  }
  return executedCode;
}

function decorateFunctionsIn(code) {
  let replacer = (match, p1, p2, offset, chain) => {
    return p1 + p2 + "@recursion_limiter\n" + p2 + "def ";
  };

  let decoratedCode = code.replace(/([\n]*)(\s*)def /g, replacer);
  return decoratedCode;
}

async function evaluatePythonFromACE(code, editorName, mode) {
  await pyodideReadyPromise;

  $.terminal.active().clear();
  pyodide.runPython(`
      import sys as __sys__
      import io as __io__
      __sys__.stdout = __io__.StringIO()
    `);

  if (mode === "_v")
    $.terminal
      .active()
      .resize(
        $.terminal.active().width(),
        document.getElementById(editorName).style.height
      );

  // Strategy : code delimited in 2 blocks
  // Block 1 : code
  // Block 2 : asserts delimited by first "# TestsWHATEVER" tag (case insensitive)
  let splitCode = code
    .replace(/#(\s*)Test(s?)[^\n]*/i, "#tests")
    .split("#tests"); // normalisation
  var mainCode = splitCode[0];
  var assertionCode = splitCode[1];
  let mainCodeLength = mainCode.split("\n").length + 1;

  echo($.terminal.active(), ps1 + runScriptPrompt);

  try {
    // foreignModulesFromImports kinda run the code once to detect the imports (that's shit, thanks pyodide)
    mainCode = await foreignModulesFromImports(
      mainCode,
      { turtle: "pyo_js_turtle" },
      editorName
    );

    let decoratedMainCode = decorateFunctionsIn(mainCode);

    pyodide.runPython(decoratedMainCode); // Running the code

    let stdout = pyodide.runPython("__sys__.stdout.getvalue()");
    pyodide.runPython("__sys__.stdout.close()");
    var testDummy = mainCode.includes("dummy_");
    if (testDummy) {
      var splitJoin = (txt, e) => txt.split(e).join("");
      console.log("ici");

      let joinInstr = [];
      let joinLib = [];
      let matchInstr = code.match(new RegExp("dummy_(\\w+)\\(", "g"));
      let importedPythonModules = code.match(
        new RegExp("#import dummy_lib_(\\w+)", "g")
      );
      if (matchInstr != null)
        for (let instruction of matchInstr)
          joinInstr.push(splitJoin(splitJoin(instruction, "dummy_"), "("));
      if (importedPythonModules != null)
        for (let instruction of importedPythonModules)
          joinLib.push(splitJoin(instruction, "#import dummy_lib_"));
      let nI = joinInstr.length;
      let nL = joinLib.length;
      stdout = "";
      if (nI > 0)
        stdout += ` ${pluralize(nI, "La", "Les")} ${pluralize(
          nI,
          "fonction"
        )} ${error(
          splitJoin(splitJoin(enumerize(joinInstr), "dummy_"), "(")
        )} ${pluralize(nI, "est", "sont")} ${pluralize(
          nI,
          "interdite"
        )} pour cet exercice !`;
      let spacer = nI > 0 && nL > 0 ? "\n" : "";
      stdout += spacer;
      if (nL > 0)
        stdout += ` ${pluralize(nL, "Le", "Les")} ${pluralize(
          nL,
          "module"
        )} ${error(splitJoin(enumerize(joinLib), "dummy_lib_"))} ${pluralize(
          nL,
          "est",
          "sont"
        )} ${pluralize(nL, "interdit")} pour cet exercice !`;
    }

    if (stdout !== "") echo($.terminal.active(), stdout);

    if (assertionCode !== undefined) {
      // Note : with the try/catch method, it is not possible to run all the tests or print and catch
      try {
        pyodide.runPython(`
        import sys as __sys__
        import io as __io__
        __sys__.stdout = __io__.StringIO()
      `);
        pyodide.runPython(assertionCode); // Running the assertions
        stdout = pyodide.runPython("__sys__.stdout.getvalue()"); // Catching and redirecting the output
        if (!testDummy && stdout !== "") echo($.terminal.active(), stdout);
      } catch (err) {
        if (!testDummy)
          echo($.terminal.active(), generateLog(err, code, mainCodeLength - 1));
      }
    }
  } catch (err) {
    if (!testDummy) echo($.terminal.active(), generateLog(err, code));
  }
}

async function evaluateHdrFile(editorName) {
  let exerciseFileContent = document.getElementById(
    "content_" + editorName
  ).innerText;
  if (hdrPlaceholderRe.test(exerciseFileContent)) {
    const matchResults = exerciseFileContent.match(
      new RegExp(hdrPlaceholderRe.source + "(.*)" + hdrPlaceholderRe.source)
    );
    if (matchResults !== null) {
      let headerCode = matchResults[1];
      pyodide.runPython(restoreEscapedCharacters(headerCode));
    }
  }
}

async function playSilent(editorName) {
  let ideClassDiv = document.getElementById("term_" + editorName).parentElement
    .parentElement;
  window.console_ready = await pyterm("#term_" + editorName, 150);
  // gives the focus to the corresponding terminal
  $("#term_" + editorName)
    .terminal()
    .focus(true);
  evaluateHdrFile(editorName);

  let stream = await ace.edit(editorName).getSession().getValue();

  localStorage.setItem(editorName, stream);

  if (ideClassDiv.dataset.exclude != "") {
    for (let instruction of ideClassDiv.dataset.exclude.split(",")) {
      pyodide.runPython(`
        def dummy_${instruction}(src):
            return src
        `);

      let re = new RegExp(`([^A-Za-z0-9_]|^)(${instruction}\\()`, "g");

      stream = stream
        .replace(re, `$1dummy_$2`)
        .replace(`import ${instruction}`, `#import dummy_lib_${instruction}`);
    }
  }
  // console.log(stream)
  return stream;
}

async function play(editorName, mode) {
  let stream = await playSilent(editorName);
  evaluateHdrFile(editorName);
  resizeTerminal(stream, mode);
  evaluatePythonFromACE(stream, editorName, mode);
}

async function start_term(idName) {
  document.getElementById(idName).className = "terminal py_mk_terminal_f";
  document.getElementById("fake_" + idName).className = "py_mk_hide";
  window.console_ready = pyterm("#" + idName);
}

function download(editorName, scriptName) {
  const generateDownloadName = (scriptName) => {
    if (scriptName != "") return `${scriptName}.py`;

    let [day, time] = new Date().toISOString().split("T");
    let hhmmss = time.split(".")[0].replace(/:/g, "-");
    return `script_${day}-${hhmmss}.py`;
  };

  let link = document.createElement("a");
  link.download = generateDownloadName(scriptName);
  let ideContent = ace.edit(editorName).getValue();
  let blob = new Blob(["" + ideContent + ""], { type: "text/plain" });
  link.href = URL.createObjectURL(blob);
  link.click();
  URL.revokeObjectURL(link.href);
}

function restart(editorName) {
  localStorage.removeItem(editorName);
  let exerciseFileContent = document.getElementById(
    `content_${editorName}`
  ).innerText;
  if (hdrPlaceholderRe.test(exerciseFileContent)) {
    const matchResults = exerciseFileContent.match(
      new RegExp(
        hdrPlaceholderRe.source + "(.*)" + hdrPlaceholderRe.source + "(.*)"
      )
    );
    if (matchResults === null) {
      var exerciseCode =
        `Missing HDR tag. Please check !\n\n` + exerciseFileContent;
    } else {
      let headerCode = matchResults[1];
      var exerciseCode = matchResults[2];
      let newline = "bksl-nl";
      while (exerciseCode.startsWith(newline)) {
        exerciseCode = exerciseCode.substring(newline.length);
      }
    }
  } else {
    var exerciseCode = exerciseFileContent;
  }
  ace
    .edit(editorName)
    .getSession()
    .setValue(restoreEscapedCharacters(exerciseCode));
}

function save(editorName) {
  localStorage.setItem(
    editorName,
    ace.edit(editorName).getSession().getValue()
  );
}

function resizeTerminal(text, mode) {
  let nlines =
    mode === "_v"
      ? Math.max(text.split(/\r\n|\r|\n/).length, 6)
      : Math.max(5, Math.min(10, text.split(/\r\n|\r|\n/).length));
  $.terminal.active().resize($.terminal.active().width(), nlines * 30);
  return nlines;
}

function getWrapperElement(filetype, editorName) {
  if (document.getElementById(filetype + editorName) === null) {
    let wrapperElement =
      document.getElementById(editorName); /* going up the DOM to IDE+buttons */
    while (wrapperElement.className !== "py_mk_ide") {
      wrapperElement = wrapperElement.parentNode;
    }
    return wrapperElement;
  }
}

function showGUI(idEditor) {
  let wrapperElement = getWrapperElement("gui_", idEditor);
  var txt = document.createElement("div");
  // txt.innerHTML='<details class="check"><summary>Fenêtre graphique</summary>\
  // <div class="highlight" id="gui_'+idEditor+'"></div></details>'
  txt.innerHTML =
    '<details open class="check"><summary>Fenêtre graphique</summary><div class = "py_mk_canvas_wrapper"><div id = "gui_' +
    idEditor +
    '"><canvas id = "gui_' +
    idEditor +
    '_tracer" width="700" height="400"></canvas><canvas id="gui_' +
    idEditor +
    '_pointer" width="700" height="400"></canvas></div></div></details>';

  wrapperElement.insertAdjacentElement("afterend", txt);
}

function showCorrection(editorName) {
  let wrapperElement = getWrapperElement("gui_", editorName);

  var txt = document.createElement("div");
  txt.setAttribute("id", `solution_${editorName}`);
  txt.innerHTML =
    '<details class="admonition check" open><summary>Solution</summary>\
    <div class="highlight" id="corr_' +
    editorName +
    '"></div></details>';

  let correctionCode = document.getElementById(`corr_content_${editorName}`);
  let url_pyfile = correctionCode.textContent;

  var _slate = document.getElementById("ace_palette").dataset.aceDarkMode;
  var _default = document.getElementById("ace_palette").dataset.aceLightMode;

  function createTheme() {
    let customLightTheme =
      _default.split("|")[1] === undefined ? "default" : _default.split("|")[1];
    let customDarkTheme =
      _slate.split("|")[1] === undefined ? "slate" : _slate.split("|")[1];
    // Correspondance between the custom and the classic palettes
    let customTheme = {
      [customLightTheme]: "default",
      [customDarkTheme]: "slate",
    };
    // Get ACE style
    var ace_style = {
      default: _default.split("|")[0],
      slate: _slate.split("|")[0],
    };
    // automatically load current palette
    let curPalette = __md_get("__palette").color["scheme"];
    return "ace/theme/" + ace_style[customTheme[curPalette]];
  }

  let ideMaximumSize = wrapperElement.dataset.max_size;

  function createACE(editorName) {
    var editor = ace.edit(editorName, {
      theme: createTheme(),
      mode: "ace/mode/python",
      autoScrollEditorIntoView: true,
      maxLines: ideMaximumSize,
      minLines: 6,
      tabSize: 4,
      readOnly: true,
      printMargin: false, // hide margins.
    });
    // Decode the backslashes into newlines for ACE editor from admonitions
    // (<div> autocloses in an admonition)
    editor.getSession().setValue(restoreEscapedCharacters(url_pyfile));
  }

  wrapperElement.insertAdjacentElement("afterend", txt);
  if (correctionCode.dataset.strudel == "")
    window.IDE_ready = createACE(`corr_${editorName}`);

  // revealing the remark from Element
  var remElement = document.getElementById("rem_content_" + editorName);
  remElement.style.display = "block";

  var fragment = document.createDocumentFragment();
  fragment.appendChild(remElement);

  document
    .getElementById("solution_" + editorName)
    .firstChild.appendChild(fragment);
}

function check(editorName, mode) {
  checkAsync(editorName, mode);
}

async function checkAsync(editorName, mode) {
  await pyodideReadyPromise;
  let interpret_code = playSilent(editorName, "");

  var code = await interpret_code;
  $.terminal.active().clear();
  echo($.terminal.active(), ps1 + runScriptPrompt);

  try {
    var testDummy = code.includes("dummy_");
    console.log(code, testDummy);
    if (testDummy) {
      var splitJoin = (txt, e) => txt.split(e).join("");

      let joinInstr = [];
      let joinLib = [];
      let matchInstr = code.match(new RegExp("dummy_(\\w+)\\(", "g"));
      let importedPythonModules = code.match(
        new RegExp("#import dummy_lib_(\\w+)", "g")
      );
      if (matchInstr != null)
        for (instruction of matchInstr)
          joinInstr.push(splitJoin(splitJoin(instruction, "dummy_"), "("));
      if (importedPythonModules != null)
        for (instruction of importedPythonModules)
          joinLib.push(splitJoin(instruction, "#import dummy_lib_"));
      let nI = joinInstr.length;
      let nL = joinLib.length;
      stdout = "";
      if (nI > 0)
        stdout += ` ${pluralize(nI, "La", "Les")} ${pluralize(
          nI,
          "fonction"
        )} ${splitJoin(
          splitJoin(enumerize(joinInstr), "dummy_"),
          "("
        )} ${pluralize(nI, "est", "sont")} ${pluralize(
          nI,
          "interdite"
        )} pour cet exercice !\n`;
      if (nL > 0)
        stdout += ` ${pluralize(nL, "Le", "Les")} ${pluralize(
          nL,
          "module"
        )} ${splitJoin(enumerize(joinLib), "dummy_lib_")} ${pluralize(
          nL,
          "est",
          "sont"
        )} ${pluralize(nL == 1, "interdit")} pour cet exercice !\n`;
      stdout += "";
    } else {
      let executedCode = await foreignModulesFromImports(
        code,
        { turtle: "pyo_js_turtle" },
        editorName
      );

      let decoratedExecutedCode = decorateFunctionsIn(executedCode);

      pyodide.runPython(decoratedExecutedCode); // Running the code

      let unittest_code = restoreEscapedCharacters(
        document.getElementById("test_term_" + editorName).textContent
      );

      if (unittest_code.includes("benchmark")) {
        pyodide.runPython(`
        import sys as __sys__
        import io as __io__
        import js
        __sys__.stdout = __io__.StringIO()

        if 'test_unitaire' not in list(globals()):
            from random import choice

        def test_unitaire(numerous_benchmark):
            global_failed = 0
            success_smb = ['🔥','✨','🌠','✅','🥇','🎖']
            fail_smb = ['🌩','🙈','🙉','⛑','🌋','💣']
            try :
                if type(numerous_benchmark[0]) not in [list, tuple]:  # just one function has to be evaluated
                    type_bench = 'multiple' 
                    numerous_benchmark = (numerous_benchmark, )

                for benchmark in numerous_benchmark:
                    failed = 0
                    print(f">>> Test de la fonction [[b;;]{benchmark[0].split('(')[0].upper()}]")
                    
                    for k, test in enumerate(benchmark, 1):
                        if eval(test):
                            print(f'Test {k} réussi :  {test} ')
                        else:
                            print(f'[[b;orange;]Test {k} échoué] : {test}')
                            failed += 1

                    if not failed :
                        print(f"[[b;green;]Bravo] vous avez réussi tous les tests {choice(success_smb)}")
                    else :
                        if failed == 1 : msg = f"{failed} test a [[b;orange;]échoué]. "
                        else : msg = f"{failed} tests ont [[b;orange;]échoué]. "
                        print(msg + f"Reprenez votre code {choice(fail_smb)}")
                        global_failed += 1
            except :
                if numerous_benchmark != []:
                    print(f"[[b;red;]Erreur :] Fonctions manquantes ou noms de fonctions incorrectes.")
                    print(f"[[b;red;]    ... ] Respectez les noms indiqués dans l'énoncé.")
                    global_failed += 1
                else:
                    print(f"🙇🏻 pas de fichier de test... Si vous êtes sur de vous, continuez à cliquer sur le gendarme.")
                    global_failed += 1
            return global_failed
        `);
        var output = await pyodide.runPythonAsync(
          unittest_code + "\ntest_unitaire(benchmark)"
        ); // Running the code OUTPUT
        var stdout = pyodide.runPython(
          "import sys as __sys__\n__sys__.stdout.getvalue()"
        );
      } else {
        console.log("declaration", unittest_code);
        var global_failed = 0;
        // splits test code into several lines without blank lines
        var testCodeTable = unittest_code
          .split("\n")
          .filter((line) => line != "");

        var testCodeTableMulti = []; // multiple lines code joined into one line
        let line = 0;
        let comment = false;
        console.log("587");
        while (line < testCodeTable.length) {
          let countPar = 0;
          let countBra = 0;
          let countCur = 0;
          let contiBool = false;
          let lineStart = line;

          // TODO : Comments are also with #
          // WARNING : testCodeTable.startsWith doesn't take into account indented code
          // This is for multiline assertions ?
          if (
            testCodeTable[line].startsWith('"""') ||
            testCodeTable[line].startsWith("'''")
          )
            comment = !comment;

          if (!comment) {
            do {
              // multilines assertions
              countPar += countParenthesis(testCodeTable[line], "(");
              countBra += countParenthesis(testCodeTable[line], "[");
              countCur += countParenthesis(testCodeTable[line], "{");
              contiBool = testCodeTable[line].endsWith("\\");
              testCodeTable[line] = testCodeTable[line]
                .replace("\\", "")
                .replace("'''", "")
                .replace('"""', "");
              line++;
              // } while (countPar !== 0 || countBra !== 0 || contiBool)
              // console.log(line, testCodeTable[line], !testCodeTable[line].includes('assert'))
            } while (
              line < testCodeTable.length &&
              !/^(\s*assert)/.test(testCodeTable[line]) &&
              (countPar !== 0 || countBra !== 0 || countCur !== 0 || contiBool)
            );
            testCodeTableMulti.push(
              testCodeTable.slice(lineStart, line).join("")
            );
          } else line++;
        }

        console.log("ici", testCodeTableMulti);

        var i = 0;
        var success = 0;
        line = 0;
        var countSoftTabs = (e) => e.startsWith("   ") || e.startsWith("    ");
        let formattedAssertCode = [];
        while (line != testCodeTableMulti.length) {
          let multiLineCode = testCodeTableMulti[line];
          while (
            line + 1 != testCodeTableMulti.length &&
            countSoftTabs(testCodeTableMulti[line + 1]) != 0
          ) {
            multiLineCode = multiLineCode + "\n" + testCodeTableMulti[line + 1];
            line++;
          }
          formattedAssertCode.push(multiLineCode);
          line++;
        }

        // number of assert BLOCKS
        var numberOfSecretTests = formattedAssertCode.filter(
          (x) => x.includes("assert") && !x.startsWith("#")
        ).length;
        var numberOfGlobalVariables = formattedAssertCode.filter(
          (x) =>
            !x.includes("assert") && !x.startsWith("#") && !x.includes("def ")
        ).length;

        var nPassedDict = {};
        var globalVariables = {};
        for (let i = 0; i < numberOfSecretTests; i++) nPassedDict[i] = 0;
        for (let i = 0; i < numberOfGlobalVariables; i++)
          globalVariables[i] = 0;

        console.log("912", formattedAssertCode);

        i = 0;
        let j = 0;
        for (let [line, command] of formattedAssertCode.entries()) {
          try {
            console.log(line, command);
            pyodide.runPython(command);
            if (
              !command.includes("assert") &&
              !command.startsWith("#") &&
              !command.includes("def ")
            ) {
              globalVariables[j] = [line, command];
              j++;
            }
            if (command.includes("assert") && !command.startsWith("#")) {
              nPassedDict[i] = [-1, command];
              i++;
              success++;
            }
          } catch (err) {
            nPassedDict[i] = [line, command];
            i++;
          }
        }

        window.n_passed = nPassedDict;
        window.global_variables = globalVariables;

        pyodide.runPython(`
from js import n_passed, global_variables
import random
import sys as __sys__
import io as __io__
__sys__.stdout = __io__.StringIO()
success_smb = ['🔥','✨','🌠','✅','🥇','🎖']

n_passed_dict = n_passed.to_py()
global_variables = global_variables.to_py()

n_passed = list(map(lambda x: x[0],n_passed_dict.values())).count(-1)

if n_passed == len(n_passed_dict):
    print(f"""[[b;green;]Bravo] {random.choice(success_smb)} : vous avez réussi tous les tests. \n\nPenser à lire le corrigé et les commentaires.""", end="")
else :
    print(f"""[[b;orange;]Dommage] : pour {len(n_passed_dict)} test{"s" if len(n_passed_dict) > 1 else ""}, il y a {n_passed} réussite{"s" if n_passed > 1 else ""}""")

    def extract_log(dico):
        for key, value in n_passed_dict.items():
            if value[0] != -1:
                return key, value[1], value[0]
        return None

    def extract_external_var(log, err_line, var_list):
        T = {}
        for _, [line, declaration] in var_list.items():
            var_name = "".join(declaration.split("=")[0].split())
            if line < err_line and var_name in log and var_name != "":
                T[var_name] = declaration
        return "\\n".join(list(T.values()))

    key, log, err_line = extract_log(n_passed_dict)

    if (ext_var := extract_external_var(log, err_line, global_variables)) != "":
        print(f"""Échec du test n°{key} : \n\n{extract_external_var(log, err_line, global_variables)} \n\n{log}""", end="")
    else:
        print(f"""Échec du test n°{key} : \n\n{log}""", end="")
`);
        if (numberOfSecretTests == success) {
          var output = 0;
        }

        var stdout = pyodide.runPython(
          "import sys as __sys__\n__sys__.stdout.getvalue()"
        ); // Catching and redirecting the output
        let elementCounter = document.getElementById("test_term_" + editorName);
        let parentCounter = elementCounter.parentElement.dataset.max;
        const nAttempts = parentCounter;
        console.log("730", "all passed");

        while (elementCounter.className !== "compteur") {
          elementCounter = elementCounter.nextElementSibling;
        }
        let [rootName, idEditor] = editorName.split("_");
        if (output === 0) dict[idEditor] = nAttempts;
        else dict[idEditor] = 1 + (idEditor in dict ? dict[idEditor] : 0);

        console.log(output, dict, nAttempts);

        if (nAttempts !== "\u221e") {
          // INFTY symbol
          elementCounter.textContent =
            Math.max(0, nAttempts - dict[idEditor]) + "/" + parentCounter;
        } else {
          elementCounter.textContent = parentCounter + "/" + parentCounter;
        }
        console.log("747", "all passed");

        if (
          dict[idEditor] == nAttempts &&
          !document.getElementById("solution_" + editorName)
        ) {
          let correctionExists = $("#corr_content_" + editorName).text(); // Extracting url from the div before Ace layer
          if (
            correctionExists !== "" ||
            document.getElementById("corr_content_" + editorName).dataset
              .strudel != ""
          ) {
            showCorrection(editorName);
          }
        }

        let nlines = resizeTerminal(stdout, mode);
        let editor = ace.edit(editorName);
        let stream = await editor.getSession().getValue();
        if (editor.session.getLength() <= nlines && mode === "_v") {
          const nslash = editor.session.getLength() - nlines + 3; // +3 takes into account shift and newlines
          for (let i = 0; i < nslash; i++) {
            stream += "\n";
          }
          editor.session.setValue(stream); // set value and reset undo history
        }
        console.log("767", "Done, all good");
      }
    }
    echo($.terminal.active(), stdout);

    console.log("all went well");
  } catch (err) {
    // Python not correct.
    err = err.toString().split("\n").slice(-7).join("\n");
    console.log("Error triggered", err);
    echo($.terminal.active(), generateLog(err, code, 0));
  }
}
