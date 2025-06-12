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
    // Primero ocultamos el modal
    hideDonateModal();

    // URL para desktop (abre en nueva pestaña)
    const desktopUrl = 'https://www.mercadopago.com.ar/home';

    // URL para mobile (intenta abrir la app)
    const mobileUrl = 'mercadopago://';

    // Detección de dispositivo móvil
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    if (isMobile) {
        // Intentamos abrir la app
        window.location.href = mobileUrl;

        // Si la app no está instalada, redirigimos a la web después de un tiempo
        setTimeout(function () {
            if (!document.hidden) {
                window.open(desktopUrl, '_blank');
            }
        }, 500);
    } else {
        // Para desktop, abrimos directamente en nueva pestaña
        window.open(desktopUrl, '_blank');
    }
}

function showIaModal() {
    document.getElementById("iaModal").style.display = "flex";
}

function hideIaModal() {
    document.getElementById("iaModal").style.display = "none";
}
async function copyText(textToCopy) {
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
        // Crear el elemento del mensaje
        const toast = document.createElement('div');
        toast.textContent = '¡Copiado!';
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        toast.style.color = 'white';
        toast.style.padding = '8px 16px';
        toast.style.borderRadius = '4px';
        toast.style.zIndex = '1000';
        toast.style.transition = 'opacity 0.5s';

        // Añadir al documento
        document.body.appendChild(toast);

        // Hacer que desaparezca después de 1.5 segundos
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 500);
        }, 1500);
    }

    return copiedSuccessfully;
}

async function copyPrompt(text) {
    const prompt = "Resume el siguiente texto de forma clara, sencilla y pedagógica, como si se lo explicaras a alguien que no está familiarizado con el tema:\n\n";
    const textToCopy = prompt + text;
    const copiedSuccessfully = await copyText(textToCopy);
    if (copiedSuccessfully) {
        showIaModal();
    }
}

/***** CATEGORIAS *******/

document.addEventListener('click', function (event) {
    const input = document.getElementById('categoria');
    const sugerencias = document.getElementById('sugerencias');

    // Si el click fue fuera del input y fuera del dropdown
    if (!input.contains(event.target) && !sugerencias.contains(event.target)) {
        sugerencias.innerHTML = '';
        sugerencias.style.display = 'none';
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('categoria');
    const sugerencias = document.getElementById('sugerencias');

    input.addEventListener('input', function () {
        const query = input.value.trim();

        if (query.length < 2) {
            sugerencias.innerHTML = '';
            return;
        }

        fetch(`/categorias?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                sugerencias.innerHTML = '';
                if (data.length === 0) {
                    sugerencias.style.display = 'none';
                    return;
                }

                data.forEach(cat => {
                    const div = document.createElement('div');
                    div.textContent = cat;
                    div.classList.add('opcion-sugerencia');
                    div.addEventListener('click', () => {
                        input.value = cat;
                        sugerencias.innerHTML = '';
                        sugerencias.style.display = 'none';
                    });
                    sugerencias.appendChild(div);
                });

                sugerencias.style.display = 'block';
            });

    });
});



  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.dd-mm-yyyy').forEach(el => {
      const utcStr = el.getAttribute('data-utc');
      if (utcStr) {
        // Extrae solo la parte de la fecha (YYYY-MM-DD)
        const match = utcStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (match) {
          const [, year, month, day] = match;
          el.innerText = `${day}/${month}/${year}`;
        } else {
          el.innerText = 'Formato inválido';
        }
      }
    });

    document.querySelectorAll('.timestamp-utc').forEach(el => {
        const utcStr = el.getAttribute('data-utc');
        if (utcStr) {
          const dateObj = new Date(utcStr);
          if (!isNaN(dateObj)) {
            el.innerText = dateObj.toLocaleDateString('utc').trim();//dateObj.toLocaleDateString('es-AR').trim();
          } else {
            el.innerText = 'Fecha inválida';
          }
        }
      });    
  });