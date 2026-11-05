"use strict";
(function () {
  const form = document.getElementById("proposal-form");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const template = document.getElementById("template");
  const subject = document.getElementById("assunto");
  const previewButton = document.getElementById("preview-button");
  const sendButton = document.getElementById("send-button");
  const message = document.getElementById("message");
  const previewEmpty = document.getElementById("preview-empty");
  const previewReady = document.getElementById("preview-ready");
  let draftId = null;
  let recipient = null;

  function notice(text, isError) {
    message.hidden = false;
    message.textContent = text;
    message.className = "notice " + (isError ? "error" : "success");
  }
  function invalidatePreview() {
    draftId = null;
    previewReady.hidden = true;
    previewEmpty.hidden = false;
    message.hidden = true;
  }
  template.addEventListener("change", function () {
    subject.value = template.options[template.selectedIndex].dataset.subject;
    invalidatePreview();
  });
  form.addEventListener("input", invalidatePreview);
  form.addEventListener("change", invalidatePreview);

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const pdf = document.getElementById("pdf").files[0];
    if (!pdf || pdf.size > 8 * 1024 * 1024) {
      notice("Selecione um PDF de até 8 MB.", true);
      return;
    }
    previewButton.disabled = true;
    previewButton.textContent = "Preparando prévia...";
    try {
      const result = await fetch("/api/preview", {
        method: "POST",
        headers: {"X-CSRF-Token": csrf},
        credentials: "same-origin",
        body: new FormData(form)
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.error || "Não foi possível gerar a prévia.");
      draftId = data.draft_id;
      recipient = data.destinatario;
      document.getElementById("review-recipient").textContent = data.destinatario;
      document.getElementById("review-subject").textContent = data.assunto;
      document.getElementById("review-pdf").textContent = data.pdf_nome + " (" + Math.ceil(data.pdf_tamanho / 1024) + " KB)";
      document.getElementById("email-frame").srcdoc = data.html;
      previewEmpty.hidden = true;
      previewReady.hidden = false;
      message.hidden = true;
      sendButton.focus();
    } catch (error) {
      invalidatePreview();
      notice(error.message || "Falha na prévia.", true);
    } finally {
      previewButton.disabled = false;
      previewButton.textContent = "Gerar prévia para revisão →";
    }
  });

  sendButton.addEventListener("click", async function () {
    if (!draftId) return;
    if (!window.confirm("Enviar agora esta proposta para " + recipient + " pelo Lark?")) return;
    const id = draftId;
    draftId = null;
    sendButton.disabled = true;
    sendButton.textContent = "Enviando pelo Lark...";
    try {
      const result = await fetch("/api/send", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf},
        credentials: "same-origin",
        body: JSON.stringify({draft_id: id, confirmacao: "ENVIAR"})
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.error || "Falha no envio.");
      notice(data.message, false);
      sendButton.textContent = "Envio aceito pelo Lark";
    } catch (error) {
      notice(error.message || "Não foi possível enviar.", true);
      sendButton.textContent = "Gere uma nova prévia para tentar novamente";
    }
  });

  document.getElementById("logout").addEventListener("click", async function () {
    try {
      await fetch("/logout", {method: "POST", headers: {"X-CSRF-Token": csrf}, credentials: "same-origin"});
    } finally {
      window.location.assign("/login");
    }
  });
})();
