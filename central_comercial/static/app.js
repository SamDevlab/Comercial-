"use strict";
(function () {
  const form = document.getElementById("proposal-form");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const template = document.getElementById("template");
  const subject = document.getElementById("assunto");
  const previewButton = document.getElementById("preview-button");
  const sendButton = document.getElementById("send-button");
  const smtpStatus = document.getElementById("smtp-status");
  const smtpCheckButton = document.getElementById("smtp-check-button");
  const smtpCheckMessage = document.getElementById("smtp-check-message");
  const message = document.getElementById("message");
  const previewEmpty = document.getElementById("preview-empty");
  const previewReady = document.getElementById("preview-ready");
  const pdfInput = document.getElementById("pdf");
  const pdfLimit = Number(pdfInput.dataset.maxBytes);
  let smtpReady = sendButton.dataset.smtpReady === "true";
  let draftId = null;
  let recipient = null;
  let previewPdfName = null;
  let previewSubject = null;

  function notice(text, isError) {
    message.hidden = false;
    message.textContent = text;
    message.className = "notice " + (isError ? "error" : "success");
  }
  function updateSmtpStatus(status) {
    const labels = {
      nao_configurado: "SMTP não configurado",
      credenciais_presentes_nao_testadas: "Credenciais presentes · não testadas",
      autenticacao_validada: "Autenticação validada",
      conexao_indisponivel: "Conexão SMTP indisponível",
      falha_autenticacao: "Falha de autenticação SMTP",
      erro_smtp: "Falha na verificação SMTP"
    };
    if (!Object.prototype.hasOwnProperty.call(labels, status)) return;
    smtpStatus.dataset.status = status;
    document.getElementById("smtp-status-label").textContent = labels[status] || "Status SMTP indisponível";
    const passed = status === "autenticacao_validada";
    const failed = ["falha_autenticacao", "conexao_indisponivel", "erro_smtp"].includes(status);
    smtpStatus.className = "status " + (passed ? "connected" : (failed ? "failed" : "offline"));
    smtpReady = passed;
    sendButton.dataset.smtpReady = passed ? "true" : "false";
    sendButton.disabled = !passed || !draftId;
    const sendHelp = document.getElementById("smtp-send-help");
    if (sendHelp) sendHelp.hidden = passed;
  }
  function invalidatePreview() {
    draftId = null;
    previewReady.hidden = true;
    previewEmpty.hidden = false;
    if (sendButton) sendButton.disabled = true;
    message.hidden = true;
  }
  template.addEventListener("change", function () {
    subject.value = template.options[template.selectedIndex].dataset.subject;
    invalidatePreview();
  });
  form.addEventListener("input", invalidatePreview);
  form.addEventListener("change", invalidatePreview);

  smtpCheckButton.addEventListener("click", async function () {
    smtpCheckButton.disabled = true;
    smtpCheckMessage.hidden = true;
    smtpCheckButton.textContent = "Testando autenticação...";
    try {
      const result = await fetch("/api/smtp/check", {
        method: "POST",
        headers: {"X-CSRF-Token": csrf},
        credentials: "same-origin"
      });
      const data = await result.json();
      if (data.status) updateSmtpStatus(data.status);
      if (!result.ok) throw new Error(data.error || "Não foi possível validar o SMTP.");
      smtpCheckMessage.hidden = false;
      smtpCheckMessage.className = "notice success";
      smtpCheckMessage.textContent = data.message;
    } catch (error) {
      smtpCheckMessage.hidden = false;
      smtpCheckMessage.className = "notice error";
      smtpCheckMessage.textContent = error.message || "Falha na verificação SMTP.";
    } finally {
      smtpCheckButton.disabled = smtpStatus.dataset.status === "nao_configurado";
      smtpCheckButton.textContent = "Testar autenticação sem enviar";
    }
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const pdf = pdfInput.files[0];
    if (!pdf || pdf.size > pdfLimit) {
      notice("Selecione um PDF de até " + pdfInput.dataset.maxLabel + ".", true);
      return;
    }
    const payload = new FormData(form);
    const controls = form.querySelectorAll("input, select, textarea");
    controls.forEach(function (control) { control.disabled = true; });
    previewButton.disabled = true;
    form.setAttribute("aria-busy", "true");
    previewButton.textContent = "Preparando prévia...";
    try {
      const result = await fetch("/api/preview", {
        method: "POST",
        headers: {"X-CSRF-Token": csrf},
        credentials: "same-origin",
        body: payload
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.error || "Não foi possível gerar a prévia.");
      draftId = data.draft_id;
      recipient = data.destinatario;
      previewSubject = data.assunto;
      previewPdfName = data.pdf_nome;
      document.getElementById("review-recipient").textContent = data.destinatario;
      document.getElementById("review-subject").textContent = data.assunto;
      document.getElementById("review-pdf").textContent = data.pdf_nome + " (" + Math.ceil(data.pdf_tamanho / 1024) + " KB)";
      document.getElementById("email-frame").srcdoc = data.html;
      previewEmpty.hidden = true;
      previewReady.hidden = false;
      sendButton.disabled = !smtpReady || !draftId;
      sendButton.textContent = "Confirmar e enviar pelo Lark";
      message.hidden = true;
      sendButton.focus();
    } catch (error) {
      invalidatePreview();
      notice(error.message || "Falha na prévia.", true);
    } finally {
      controls.forEach(function (control) { control.disabled = false; });
      form.removeAttribute("aria-busy");
      previewButton.disabled = false;
      previewButton.textContent = "Gerar prévia para revisão →";
    }
  });

  sendButton.addEventListener("click", async function () {
    if (!draftId) return;
    if (!window.confirm(
      "Confirme o envio pelo Lark:\n\nPara: " + recipient +
      "\nAssunto: " + previewSubject + "\nPDF: " + previewPdfName + "\n\nEnviar agora?"
    )) return;
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
      if (data.status) updateSmtpStatus(data.status);
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
