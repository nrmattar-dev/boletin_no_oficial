function toggleTextoResumido(i) {
    const moreText = document.getElementById("more-" + i);
    const dots = document.getElementById("dots-" + i);
    const btnText = document.getElementById("btn-" + i);

    if (moreText.style.display === "none") {
        moreText.style.display = "inline";
        dots.style.display = "none";
        btnText.textContent = "Mostrar menos";
    } else {
        moreText.style.display = "none";
        dots.style.display = "inline";
        btnText.textContent = "Mostrar más";
    }
}

function showDonateModal() {
    document.getElementById("donateModal").style.display = "flex";
}

function hideDonateModal() {
    document.getElementById("donateModal").style.display = "none";
}

function donateNow() {
    window.open('https://www.mercadopago.com.ar/home', '_blank');
    hideDonateModal();
}

function showIaModal() {
    document.getElementById("iaModal").style.display = "flex";
}

function hideIaModal() {
    document.getElementById("iaModal").style.display = "none";
}

async function copyPromptAndText(originalText) {
    const prompt = "Resume el siguiente texto de forma clara, sencilla y pedagógica, como si se lo explicaras a alguien que no está familiarizado con el tema:\n\n";
    const textToCopy = prompt + originalText;
    let copiedSuccessfully = false;

    try {
        await navigator.clipboard.writeText(textToCopy);
        copiedSuccessfully = true;
    } catch (err) {
        try {
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.style.position = 'fixed';
            textarea.style.top = 0;
            textarea.style.left = 0;
            textarea.style.opacity = 0;
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            copiedSuccessfully = true;
        } catch (err2) {
            alert('Hubo un error al copiar el texto. Por favor, intenta copiarlo manualmente.');
        }
    }

    if (copiedSuccessfully) {
        showIaModal();
    }
}
