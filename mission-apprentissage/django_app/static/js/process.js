document.addEventListener("DOMContentLoaded", function () {
  const epubForm = document.getElementById("epubForm");
  const uploadZone = document.getElementById("uploadZone");
  const epubFileInput = document.getElementById("epubFile");
  const filePreview = document.getElementById("filePreview");
  const fileCount = document.getElementById("fileCount");
  const previewGrid = document.getElementById("previewGrid");
  const submitBtn = document.getElementById("submitBtn");
  const resultSection = document.getElementById("resultSection");
  const analysisResults = document.getElementById("analysisResults");
  const errorSection = document.getElementById("errorSection");
  const errorMessage = document.getElementById("errorMessage");

  let selectedFiles = [];

  const MODELS = [
    { key: "salesforce_blip", name: "Salesforce BLIP", color: "primary", icon: "robot", },
    { key: "florence2", name: "Florence-2", color: "success", icon: "robot", },
    { key: "git_large", name: "GIT Large", color: "info", icon: "robot", },
  ];

  // Fonction pour formater la taille des fichiers
  function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  }

  function extractDescription(modelResult) {
    if (!modelResult) {
      return "Erreur: Aucun résultat disponible pour ce modèle";
    }

    // Si c'est une chaîne, retourner directement
    if (typeof modelResult === "string") {
      return modelResult;
    }

    // Uniquement french_description
    if (
      modelResult.french_description &&
      modelResult.french_description.trim() !== ""
    ) {
      return modelResult.french_description;
    }

    // Vérifier les résultats imbriqués
    if (
      modelResult.results &&
      Array.isArray(modelResult.results) &&
      modelResult.results.length > 0
    ) {
      const firstResult = modelResult.results[0];
      if (
        firstResult?.french_description &&
        firstResult.french_description.trim() !== ""
      ) {
        return firstResult.french_description;
      }
    }

    // PAS DE FALLBACK - Message d'erreur explicite
    return "Erreur: Description française non disponible pour ce modèle";
  }

  // Générer une carte de résultat pour un modèle avec gestion des erreurs
  function generateModelCard(modelName, description, color, icon) {
    const isError = description.startsWith("Erreur:");
    const cardClass = isError ? "border-danger bg-light-danger" : "border";
    const textClass = isError ? "text-danger" : "";
    const iconToUse = isError ? "exclamation-triangle" : icon;

    return `
            <div class="mb-3 p-3 ${cardClass} rounded">
                <h6 class="text-${color} mb-2">
                    <i class="fas fa-${iconToUse} me-2"></i>
                    ${modelName}
                </h6>
                <p class="mb-0 ${textClass}">${description}</p>
            </div>
        `;
  }

  function createPreviewCard(file, index) {
    const col = document.createElement("div");
    col.className = "col-md-4 col-sm-6";

    const card = document.createElement("div");
    card.className = "card position-relative";
    card.style.cssText = "height: 200px;";

    const reader = new FileReader();
    reader.onload = function (e) {
      card.innerHTML = `
                <img src="${e.target.result}" class="card-img-top" style="height: 150px; object-fit: cover;" alt="${file.name}">
                <div class="card-body p-2">
                    <small class="text-truncate d-block" title="${file.name}">${file.name}</small>
                    <small class="text-muted">${formatFileSize(file.size)}</small>
                </div>
                <button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 m-2" onclick="removeFile(${index})" style="z-index: 10;">
                    <i class="fas fa-times"></i>
                </button>
            `;
    };
    reader.readAsDataURL(file);

    col.appendChild(card);
    return col;
  }

  function addFiles(files) {
    const validFiles = files.filter((file) =>
      file.name.toLowerCase().endsWith(".epub"),
    );
    if (validFiles.length === 0) {
      showError("Veuillez sélectionner des fichiers EPUB valides.");
      return;
    }
    selectedFiles = [...selectedFiles, ...validFiles];
    updateFilePreview();
  }

  function updateFilePreview() {
    if (selectedFiles.length === 0) {
      filePreview.style.display = "none";
      return;
    }

    fileCount.textContent = selectedFiles.length;
    previewGrid.innerHTML = "";

    selectedFiles.forEach((file, index) => {
      previewGrid.appendChild(createPreviewCard(file, index));
    });

    filePreview.style.display = "block";

    // Mettre à jour l'input file
    const dataTransfer = new DataTransfer();
    selectedFiles.forEach((file) => dataTransfer.items.add(file));
    epubFileInput.files = dataTransfer.files;
  }

  // Gestion Drag and Drop
  uploadZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });
  uploadZone.addEventListener("dragleave", function (e) {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
  });
  uploadZone.addEventListener("drop", function (e) {
    e.preventDefault();
    uploadZone.classList.remove("dragover");

    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  });

  // Upload file click
  uploadZone.addEventListener("click", function (e) {
    if (!e.target.closest("button")) {
      epubFileInput.click();
    }
  });

  // Changement de fichier
  epubFileInput.addEventListener("change", function () {
    if (this.files.length > 0) {
      addFiles(Array.from(this.files));
    }
  });

  window.removeFile = function (index) {
    selectedFiles.splice(index, 1);
    updateFilePreview();
  };

  // Soumission du formulaire
  epubForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    if (selectedFiles.length === 0) {
      showError("Veuillez sélectionner au moins un fichier EPUB.");
      return;
    }

    // Cacher les sections de résultats précédents
    resultSection.style.display = "none";
    errorSection.style.display = "none";

    // Désactiver le bouton pendant le traitement
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin me-2"></i>Analyse en cours... Cela peut prendre jusqu\'à 2 minutes';

    try {
      const token = localStorage.getItem('access_token');
      if (!token) { redirectToLogin(); return; }

      const buildFormData = () => {
        const formData = new FormData();
        selectedFiles.forEach((file) => formData.append("epub", file));
        return formData;
      };

      let response = await fetch(API_PROCESS_EPUB_URL, {
        method: "POST",
        body: buildFormData(),
        headers: {
          "X-CSRFToken": CSRF_TOKEN,
          "Authorization": `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (!refreshed) { redirectToLogin(); return; }
        response = await fetch(API_PROCESS_EPUB_URL, {
          method: "POST",
          body: buildFormData(),
          headers: {
            "X-CSRFToken": CSRF_TOKEN,
            "Authorization": `Bearer ${localStorage.getItem('access_token')}`,
          },
        });
      }

      const data = await response.json();

      if (response.ok && data.success) {
        const taskId = data.results.task_id;
        if (taskId) {
          showUploadSuccess(taskId);
        } else {
          displayResults(data.results, selectedFiles);
        }
      } else if (response.status === 408) {
        showError(
          "Le traitement prend plus de temps que prévu. Les modèles sont peut-être en train de se charger. Veuillez réessayer.",
        );
      } else {
        showError(data.error || "Une erreur est survenue lors de l'analyse.");
      }
    } catch (error) {
      showError("Erreur de connexion: " + error.message);
    } finally {
      // Réactiver le bouton
      submitBtn.disabled = false;
      submitBtn.innerHTML =
        '<i class="fas fa-magic me-2"></i>Analyser le fichier EPUB';
    }
  });

  function displayResults(data, files) {
    console.log("Data received:", data);

    if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
      analysisResults.innerHTML =
        '<div class="alert alert-warning">Aucun résultat disponible</div>';
      resultSection.style.display = "block";
      return;
    }

    let htmlResult = "";

    // Itérer sur chaque fichier EPUB
    Object.entries(data).forEach(([filename, epubResults]) => {
      htmlResult += `
            <div class="card mb-4 shadow-sm">
                <div class="card-header bg-info text-white">
                    <h4 class="mb-0">
                        <i class="fas fa-book me-2"></i>
                        ${filename}
                    </h4>
                </div>
                <div class="card-body">
        `;

      // Vérifier les erreurs au niveau EPUB
      if (epubResults && typeof epubResults === "object" && epubResults.error) {
        htmlResult += `<div class="alert alert-danger">${epubResults.error}</div>`;
      } else {
        // Extraire les images des résultats EPUB
        const imagesData = epubResults.images || epubResults;
        const imageKeys = Object.keys(imagesData)
          .filter((key) => key.startsWith("image_"))
          .sort(
            (a, b) =>
              Number(a.replace("image_", "")) - Number(b.replace("image_", "")),
          );

        if (imageKeys.length === 0) {
          htmlResult +=
            '<div class="alert alert-warning">Aucune image trouvée dans ce fichier EPUB</div>';
        } else {
          htmlResult += `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        ${imageKeys.length} image(s) trouvée(s) dans ce fichier EPUB
                    </div>
                `;

          // Générer une carte pour chaque image
          imageKeys.forEach((imageKey, idx) => {
            const imageData = imagesData[imageKey];
            htmlResult += generateEpubImageCard(imageData, imageKey, idx);
          });
        }
      }

      htmlResult += "</div></div>";
    });

    analysisResults.innerHTML = htmlResult;
    resultSection.style.display = "block";
    resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Générer une carte pour une image dans le contexte EPUB
  function generateEpubImageCard(imageData, imageKey, imgIndex) {
    const imageLabel = imageKey.replace("_", " ").toUpperCase();

    let html = `
        <div class="card mb-3 border-secondary">
            <div class="card-header bg-secondary text-white">
                <h6 class="mb-0">
                    <i class="fas fa-image me-2"></i>
                    ${imageLabel}
                </h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-12">
                        <p class="text-muted small mb-3">
                            <i class="fas fa-language me-2"></i>
                            Descriptions en français par modèle IA:
                        </p>
                    </div>
                </div>
    `;

    // Générer les cartes de modèles
    MODELS.forEach((model) => {
      const description = extractDescription(imageData[model.key]);
      html += `<div class="col-12">${generateModelCard(
        model.name,
        description,
        model.color,
        model.icon,
      )}</div>`;
    });

    html += "</div></div>";
    return html;
  }

  function showUploadSuccess(taskId) {
    resultSection.style.display = "block";
    analysisResults.innerHTML = `
      <div class="alert alert-success">
        <h5><i class="fas fa-check-circle me-2"></i>Fichier EPUB envoyé avec succes</h5>
        <p>Le traitement des images est en cours en arriere-plan.</p>
      </div>
      <div class="d-grid gap-2">
        <a href="/review/?task_id=${taskId}" class="btn btn-primary btn-lg">
          <i class="fas fa-table me-2"></i>
          Voir les descriptions
        </a>
      </div>
    `;
    resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorSection.style.display = "block";
    resultSection.style.display = "none";

    // Scroll vers l'erreur
    errorSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});