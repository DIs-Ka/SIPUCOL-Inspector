
const normalize = value =>
  String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();


const targetButtons = new Set([
  "superficie del puente",
  "juntas de dilatacion",
  "bordillo",
  "barandas",
  "aletas",
  "estribos",
  "apoyos",
  "losa",
  "vigas",
  "senalizacion",
  "puente en general"
]);


function hide(element) {
  if (!element || element === document.body) return;

  element.style.setProperty("display", "none", "important");
  element.style.setProperty("height", "0", "important");
  element.style.setProperty("min-height", "0", "important");
  element.style.setProperty("margin", "0", "important");
  element.style.setProperty("padding", "0", "important");
  element.style.setProperty("border", "0", "important");
  element.style.setProperty("overflow", "hidden", "important");
  element.setAttribute("data-photo-send-bar-hidden", "true");
}


function findTextElement(fragment) {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT
  );

  while (walker.nextNode()) {
    const node = walker.currentNode;

    if (normalize(node.nodeValue).includes(fragment)) {
      return node.parentElement;
    }
  }

  return null;
}


function matchingButtons(container) {
  return [
    ...container.querySelectorAll("button, [role='button']")
  ].filter(element =>
    targetButtons.has(normalize(element.textContent))
  );
}


function hidePhotoSendBar() {
  const title = findTextElement("enviar foto a evaluacion");

  if (!title) return false;

  /*
  Caso principal:
  busca el contenedor más pequeño que incluya
  título, Destino y los botones de componentes.
  */
  let current = title;

  for (let level = 0; level < 9 && current; level += 1) {
    const text = normalize(current.textContent);
    const buttons = matchingButtons(current);

    if (
      text.includes("enviar foto a evaluacion") &&
      text.includes("destino:") &&
      buttons.length >= 3 &&
      !text.includes("carpeta actual") &&
      !text.includes("ver grande")
    ) {
      hide(current);
      return true;
    }

    current = current.parentElement;
  }

  /*
  Respaldo:
  oculta por separado la cabecera y la fila
  de botones cuando React las divide.
  */
  const destination = findTextElement("destino:");

  if (title.parentElement) {
    hide(title.parentElement);
  } else {
    hide(title);
  }

  if (destination) {
    hide(destination.parentElement || destination);
  }

  const buttons = [
    ...document.querySelectorAll("button, [role='button']")
  ].filter(element =>
    targetButtons.has(normalize(element.textContent))
  );

  if (buttons.length >= 3) {
    let row = buttons[0].parentElement;

    while (
      row &&
      row.parentElement &&
      matchingButtons(row.parentElement).length >= 3 &&
      !normalize(row.parentElement.textContent).includes("carpeta actual") &&
      !normalize(row.parentElement.textContent).includes("ver grande")
    ) {
      row = row.parentElement;
    }

    hide(row);

    for (const button of buttons) {
      hide(button);
    }
  }

  return true;
}


let scheduled = false;

function scheduleCleanup() {
  if (scheduled) return;

  scheduled = true;

  requestAnimationFrame(() => {
    scheduled = false;
    hidePhotoSendBar();
  });
}


function start() {
  hidePhotoSendBar();

  const observer = new MutationObserver(scheduleCleanup);

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}


if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start, { once: true });
} else {
  start();
}
