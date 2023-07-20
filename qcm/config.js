//window.MathJax = {
//  tex: {
//    inlineMath: [["\\(", "\\)"]],
//    displayMath: [["\\[", "\\]"]],
//    processEscapes: true,
//    processEnvironments: true,
//  },
//  options: {
//    ignoreHtmlClass: ".*|",
//    processHtmlClass: "arithmatex",
//  },
//};
window.MathJax = {
  startup: {
    ready: () => {
      console.log("MathJax is loaded, but not yet initialized");
      MathJax.startup.defaultReady();
      console.log("MathJax is initialized, and the initial typeset is queued");
    },
  },
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
  },
};
