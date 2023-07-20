function richTextFormat(content, style, color = "", background = "") {
  return `[[${style};${color};${background}]${content}]`;
}

let error = (content) => richTextFormat(content, "b", "red");
let warning = (content) => richTextFormat(content, "", "orange");
let stress = (content) => richTextFormat(content, "b");
let info = (content) => richTextFormat(content, "", "grey");
let italic = (content) => richTextFormat(content, "i");
let errorMessage = (errorType, lineNumber, log) => {
  return ` Python a renvoyé une ${error(
    errorType
  )} à la ligne ${lineNumber} :\n\n ${italic(log)}`;
};

let runScriptPrompt = info("%Script exécuté");
let ps1 = ">>> ";
let ps2 = "... ";

function countParenthesis(string, separator = "(") {
  const matching_separator = { "(": ")", "[": "]", "{": "}" };
  let countChar = (str, c) => str.split(c).length - 1;
  return (
    countChar(string, separator) -
    countChar(string, matching_separator[separator])
  );
}

function removeRecursionWrapperFrom(errorlog) {
  let indexRecursionWrapper = -1;
  for (let i = 0; i < errorlog.length; i++) {
    if (errorlog[i].includes("RecursionWrapper")) indexRecursionWrapper = i;
  }

  if (indexRecursionWrapper != -1) errorlog.splice(indexRecursionWrapper, 1);

  return errorlog;
}

function generateAssertionLog(errorLineInLog, code) {
  // PROBLEME s'il y a des parenthèses non correctement parenthésées dans l'expression à parser !
  let codeTable = code.split("\n");
  errorLineInLog -= 1;

  let endErrLineLog = errorLineInLog;
  let countPar = 0;
  do {
    // multilines assertions
    countPar += countParenthesis(codeTable[endErrLineLog]);
    endErrLineLog++;
  } while (countPar !== 0 && !/^(\s*assert)/.test(codeTable[endErrLineLog]));

  return `${codeTable
    .slice(errorLineInLog, endErrLineLog)
    .join(" ")
    .replace("assert ", "")}`;
}

function generateErrorLog(
  errorTypeLog,
  errorLineInLog,
  code,
  mainCodeLength = 0
) {
  let conversionTable = {
    AssertionError: "Erreur d'assertion",
    SyntaxError: "Erreur de syntaxe",
    ModuleNotFoundError: "Erreur de chargement de module",
    IndexError: "Erreur d'indice",
    KeyError: "Erreur de clé",
    IndentationError: "Erreur d'indentation",
    AttributeError: "Erreur de référence",
    TypeError: "Erreur de type",
    NameError: "Erreur de nommage",
    ZeroDivisionError: "Division par zéro",
    MemoryError: "Dépassement mémoire",
    OverflowError: "Taille maximale de flottant dépassée",
    TabError: "Mélange d'indentations et d'espaces",
    RecursionError: "Erreur de récursion",
    ValueError: "Valeur incorrecte",
    UnboundLocalError: "Variable non définie",
  };
  // Ellipsis is triggered when dots (...) are used
  errorTypeLog += errorTypeLog.includes("Ellipsis")
    ? " (issue with the dots ...)"
    : "";
  for (const errorType in conversionTable) {
    if (errorTypeLog.includes(errorType)) {
      if (errorType != "AssertionError") {
        return errorMessage(
          conversionTable[errorType],
          errorLineInLog,
          errorTypeLog
        );
      }
      let prefix = "";
      let isPublicTests = mainCodeLength != 0;
      if (isPublicTests) prefix += stress(" Erreur avec les tests publics :\n");

      let isNoDescriptionInAssertion = errorTypeLog === "AssertionError";
      if (isNoDescriptionInAssertion) {
        errorTypeLog = `${errorTypeLog}: test ${warning(
          generateAssertionLog(errorLineInLog + mainCodeLength, code)
        )} échoué`;
      }

      return (
        prefix +
        errorMessage(
          conversionTable[errorType],
          errorLineInLog + mainCodeLength,
          errorTypeLog
        )
      );
    }
  }
}

function generateLog(err, code, mainCodeLength = 0) {
  err = String(err).split("\n");
  let p = -2;
  let lastLogs = err.slice(p, -1);
  // catching relevant Exception logs

  while (
    !/line\s[0-9]+($|[^)]+)/.test(lastLogs[0]) ||
    lastLogs[0].includes("RecursionWrapper")
  ) {
    lastLogs = err.slice(p, -1);
    p--;
  }

  var errLineLog = lastLogs[0].split(",");
  // catching line number of Exception
  let i = 0;
  while (!errLineLog[i].includes("line")) i++;
  // When <exec> appears, an extra line is executed on Pyodide side (correct for it with -1) // corrected in version XXX ?
  let shift = errLineLog[0].includes("<exec>") ? -1 : 0;
  //let shift = 0;
  errLineLog =
    Number(errLineLog[i].slice(5 + errLineLog[i].indexOf("line"))) + shift; //+ src; // get line number

  lastLogs = removeRecursionWrapperFrom(lastLogs);

  // catching multiline Exception logs (without line number)
  var errorTypeLog = lastLogs[1];
  p = 2;
  while (p < lastLogs.length) {
    errorTypeLog = errorTypeLog + "\n" + " " + lastLogs[p];
    p++;
  }
  console.log(errorTypeLog, errLineLog, code);
  console.log(mainCodeLength);
  return generateErrorLog(errorTypeLog, errLineLog, code, mainCodeLength);
}

const pluralize = (numberOfItems, singularForm, pluralForm = "s") => {
  let plural = pluralForm != "s" ? pluralForm : singularForm + "s";
  return numberOfItems <= 1 ? singularForm : plural;
};

const enumerize = (liste) =>
  liste.length == 1
    ? liste.join("")
    : liste.slice(0, -1).join(", ") + " et " + liste.slice(-1);

function restoreEscapedCharacters(codeContent) {
  return codeContent
    .replace(/bksl-nl/g, "\n")
    .replace(/py-und/g, "_")
    .replace(/py-str/g, "*");
}
