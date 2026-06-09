document.addEventListener('DOMContentLoaded', function() {
    // Constantes
    const MODELS = [
        { key: 'salesforce_blip', name: 'Salesforce BLIP', color: 'primary' },
        { key: 'florence2', name: 'Florence-2', color: 'success' },
        { key: 'git_large', name: 'GIT Large', color: 'info' }
    ];

    // Éléments DOM
    const reviewTableBody = document.getElementById('reviewTableBody');
    const validateAllBtn = document.getElementById('validateAllBtn');
    const searchInput = document.getElementById('searchInput');
    const modelFilter = document.getElementById('modelFilter');
    const statusFilter = document.getElementById('statusFilter');
    const clearFiltersBtn = document.getElementById('clearFilters');
    const showOnlyUnvalidated = document.getElementById('showOnlyUnvalidated');
    const validatedCount = document.getElementById('validatedCount');
    const totalCount = document.getElementById('totalCount');
    const progressBar = document.getElementById('progressBar');

    // État global
    let imagesData = [];
    let taskId = null;

    // 1. Initialisation : charger les données
    async function init() {
        // Récupérer task_id depuis l'URL
        const urlParams = new URLSearchParams(window.location.search);
        taskId = urlParams.get('task_id') || (typeof TASK_ID !== 'undefined' ? TASK_ID : null);

        if (!taskId) {
            showError('Task ID manquant');
            return;
        }

        // Charger les données depuis sessionStorage ou API
        await loadData();

        // Rendre le tableau
        renderTable();

        // Attacher les événements
        attachEventListeners();

        // Mettre à jour les stats
        updateStats();
    }

    // 2. Charger les données depuis l'API DB
    async function loadData() {
        try {
            const response = await fetchWithAuth(`${FASTAPI_URL}/api/description/${taskId}`);

            if (!response) return;

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Erreur API (${response.status}): ${errorText}`);
            }

            const data = await response.json();
            imagesData = parseImagesData(data);

        } catch (error) {
            showError('Impossible de charger les données : ' + error.message);
        }
    }

    // 3. Parser les données du format API DB vers format tableau
    function parseImagesData(data) {
        return data.images.map((image, index) => {
            // Construire les descriptions par model_key
            const descriptions = {
                salesforce_blip: 'En cours de chargement...',
                florence2: 'En cours de chargement...',
                git_large: 'En cours de chargement...'
            };

            let validatedModel = null;
            let humanDescription = '';
            let isValidated = false;
            let isCustom = false;

            image.descriptions.forEach(desc => {
                if (desc.is_written_by_human) {
                    humanDescription = desc.description_text;
                    isCustom = true;
                    isValidated = desc.validated_by_human;
                } else if (desc.model_key) {
                    descriptions[desc.model_key] = desc.description_text;
                    if (desc.validated_by_human) {
                        validatedModel = desc.model_key;
                        isValidated = true;
                    }
                }
            });

            return {
                index: index,
                imageId: image.image_id,
                filename: image.image_file_name,
                descriptions: descriptions,
                selectedModel: validatedModel,
                customDescription: humanDescription,
                isValidated: isValidated,
                isCustom: isCustom
            };
        });
    }

    // 5. Rendre le tableau
    function renderTable(filteredData = null) {
        const dataToRender = filteredData || imagesData;

        if (dataToRender.length === 0) {
            reviewTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-5">
                        <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                        <p class="text-muted">Aucune image trouvée</p>
                    </td>
                </tr>
            `;
            return;
        }

        reviewTableBody.innerHTML = dataToRender.map(image => {
            return `
                <tr data-image-index="${image.index}"
                    class="${image.isValidated ? 'table-success' : ''}">

                    <!-- Numéro -->
                    <td class="text-center fw-bold">${image.index + 1}</td>

                    <!-- Image (icône ou miniature) -->
                    <td class="text-center">
                        <i class="fas fa-image fa-2x text-muted"></i>
                    </td>

                    <!-- Fichier -->
                    <td>
                        <small class="text-muted">${image.filename}</small>
                    </td>

                    <!-- Salesforce BLIP -->
                    <td>${generateModelCell(image, 'salesforce_blip', MODELS[0])}</td>

                    <!-- Florence-2 -->
                    <td>${generateModelCell(image, 'florence2', MODELS[1])}</td>

                    <!-- GIT Large -->
                    <td>${generateModelCell(image, 'git_large', MODELS[2])}</td>

                    <!-- Description personnalisée -->
                    <td>${generateCustomCell(image)}</td>

                    <!-- Statut -->
                    <td class="text-center">${generateStatusBadge(image)}</td>
                </tr>
            `;
        }).join('');

        // Attacher les événements après le rendu
        attachRowEventListeners();
    }

    // 6. Générer une cellule de modèle avec radio
    function generateModelCell(image, modelKey, modelInfo) {
        const description = image.descriptions[modelKey];
        const isError = description.startsWith('Erreur:');
        const isSelected = image.selectedModel === modelKey;
        const radioId = `radio-${image.index}-${modelKey}`;

        if (isError) {
            return `
                <div class="text-danger small">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    ${description}
                </div>
            `;
        }

        return `
            <div class="form-check">
                <input class="form-check-input model-radio"
                       type="radio"
                       name="model-${image.index}"
                       id="${radioId}"
                       value="${modelKey}"
                       data-image-index="${image.index}"
                       ${isSelected ? 'checked' : ''}
                       ${image.isValidated ? 'disabled' : ''}>
                <label class="form-check-label small" for="${radioId}">
                    <span class="badge bg-${modelInfo.color} badge-sm mb-1">
                        ${modelInfo.name}
                    </span>
                    <div class="description-preview">
                        ${truncateText(description, 100)}
                    </div>
                </label>
            </div>
        `;
    }

    // 7. Générer la cellule personnalisée
    function generateCustomCell(image) {
        const isSelected = image.isCustom;
        const radioId = `radio-${image.index}-custom`;

        return `
            <div class="form-check mb-2">
                <input class="form-check-input custom-radio"
                       type="radio"
                       name="model-${image.index}"
                       id="${radioId}"
                       value="custom"
                       data-image-index="${image.index}"
                       ${isSelected ? 'checked' : ''}
                       ${image.isValidated ? 'disabled' : ''}>
                <label class="form-check-label" for="${radioId}">
                    <span class="badge bg-warning">Personnalisée</span>
                </label>
            </div>
            <textarea class="form-control form-control-sm custom-description-input"
                      rows="3"
                      placeholder="Écrire une description..."
                      data-image-index="${image.index}"
                      ${!isSelected || image.isValidated ? 'disabled' : ''}>${image.customDescription}</textarea>
        `;
    }

    // 8. Générer le badge de statut
    function generateStatusBadge(image) {
        if (image.isValidated) {
            return `<span class="badge bg-success"><i class="fas fa-check me-1"></i>Validé</span>`;
        }

        if (image.selectedModel || image.isCustom) {
            return `<span class="badge bg-info"><i class="fas fa-clock me-1"></i>Sélectionné</span>`;
        }

        return `<span class="badge bg-warning"><i class="fas fa-hourglass-half me-1"></i>À valider</span>`;
    }

    // 9. Attacher les événements aux radios et inputs
    function attachRowEventListeners() {
        // Radios des modèles
        document.querySelectorAll('.model-radio').forEach(radio => {
            radio.addEventListener('change', function() {
                const imageIndex = parseInt(this.dataset.imageIndex);
                const modelKey = this.value;

                imagesData[imageIndex].selectedModel = modelKey;
                imagesData[imageIndex].isCustom = false;

                // Désactiver le textarea
                const textarea = document.querySelector(`textarea[data-image-index="${imageIndex}"]`);
                if (textarea) textarea.disabled = true;

                updateStats();
            });
        });

        // Radios personnalisées
        document.querySelectorAll('.custom-radio').forEach(radio => {
            radio.addEventListener('change', function() {
                const imageIndex = parseInt(this.dataset.imageIndex);

                imagesData[imageIndex].selectedModel = null;
                imagesData[imageIndex].isCustom = true;

                // Activer le textarea
                const textarea = document.querySelector(`textarea[data-image-index="${imageIndex}"]`);
                if (textarea) textarea.disabled = false;

                updateStats();
            });
        });

        // Textareas
        document.querySelectorAll('.custom-description-input').forEach(textarea => {
            textarea.addEventListener('input', function() {
                const imageIndex = parseInt(this.dataset.imageIndex);
                imagesData[imageIndex].customDescription = this.value;
            });
        });
    }

    // 10. Valider toutes les sélections
    validateAllBtn.addEventListener('click', async function() {
        // Vérifier que toutes les images ont une sélection
        const unselected = imagesData.filter(img =>
            !img.isValidated && !img.selectedModel && !img.isCustom
        );

        if (unselected.length > 0) {
            showError(`${unselected.length} image(s) n'ont pas de sélection. Veuillez sélectionner une description pour chaque image.`);
            return;
        }

        // Vérifier que les descriptions personnalisées ne sont pas vides
        const emptyCustom = imagesData.filter(img =>
            img.isCustom && (!img.customDescription || img.customDescription.trim() === '')
        );

        if (emptyCustom.length > 0) {
            showError(`${emptyCustom.length} description(s) personnalisée(s) sont vides.`);
            return;
        }

        // Préparer les données pour l'API
        const validationData = {
            validated_descriptions: imagesData
                .filter(img => !img.isValidated)
                .map(img => ({
                    image_index: img.index,
                    text: img.isCustom ? img.customDescription : img.descriptions[img.selectedModel],
                    model: img.isCustom ? null : mapModelKey(img.selectedModel),
                    is_written_by_ai: !img.isCustom,
                    is_written_by_human: img.isCustom
                }))
        };

        // Désactiver le bouton
        validateAllBtn.disabled = true;
        validateAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Validation en cours...';

        try {
            const response = await fetchWithAuth(`${FASTAPI_URL}/api/description/${taskId}/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(validationData)
            });

            if (!response) return;

            const data = await response.json();

            if (response.ok && data.success) {
                // Marquer toutes les images comme validées
                imagesData.forEach(img => {
                    if (!img.isValidated) img.isValidated = true;
                });

                // Re-rendre le tableau
                renderTable();
                updateStats();

                // Notification de succès
                showNotification(`✅ ${data.validated_count} image(s) validée(s) avec succès !`, 'success');

                // Nettoyer le cache
                sessionStorage.removeItem(`task_${taskId}`);

            } else {
                showError(data.detail || 'Erreur lors de la validation');
            }

        } catch (error) {
            showError('Erreur de connexion: ' + error.message);
        } finally {
            validateAllBtn.disabled = false;
            validateAllBtn.innerHTML = '<i class="fas fa-check-circle me-2"></i>Valider toutes les sélections';
        }
    });

    // 11. Générer l'EPUB modifié
    document.getElementById('generateEpubBtn').addEventListener('click', async function () {
        const btn = this;
        const statusDiv = document.getElementById('generateStatus');

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Génération en cours...';
        statusDiv.style.display = 'none';

        try {
            const response = await fetchWithAuth(`${FASTAPI_URL}/api/description/add_descriptions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id_redis: taskId }),
            });

            if (!response) return;

            if (response.ok) {
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition') || '';
                const match = contentDisposition.match(/filename[^;=\n]*=(?:(\\?['"])(.*?)\1|([^;\n]*))/);
                const filename = match ? (match[2] || match[3]) : 'modified.epub';

                const objectUrl = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = objectUrl;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(objectUrl);

                statusDiv.className = 'alert alert-success mt-3';
                statusDiv.textContent = 'EPUB généré avec succès ! Téléchargement en cours...';
                statusDiv.style.display = 'block';
            } else {
                const data = await response.json();
                statusDiv.className = 'alert alert-danger mt-3';
                statusDiv.textContent = data.detail || 'Erreur lors de la génération';
                statusDiv.style.display = 'block';
            }
        } catch {
            statusDiv.className = 'alert alert-danger mt-3';
            statusDiv.textContent = 'Erreur de connexion au serveur';
            statusDiv.style.display = 'block';
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-download me-2"></i>Générer l\'EPUB modifié';
        }
    });

    // 12. Filtres et recherche
    function applyFilters() {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedModel = modelFilter.value;
        const selectedStatus = statusFilter.value;
        const onlyUnvalidated = showOnlyUnvalidated.checked;

        const filtered = imagesData.filter(image => {
            // Filtre de recherche
            if (searchTerm) {
                const hasMatch = Object.values(image.descriptions).some(desc =>
                    desc.toLowerCase().includes(searchTerm)
                );
                if (!hasMatch && !image.customDescription.toLowerCase().includes(searchTerm)) {
                    return false;
                }
            }

            // Filtre par modèle
            if (selectedModel && image.selectedModel !== selectedModel) {
                return false;
            }

            // Filtre par statut
            if (selectedStatus === 'pending' && image.isValidated) return false;
            if (selectedStatus === 'validated' && !image.isValidated) return false;

            // Filtre non validées seulement
            if (onlyUnvalidated && image.isValidated) return false;

            return true;
        });

        renderTable(filtered);
    }

    searchInput.addEventListener('input', applyFilters);
    modelFilter.addEventListener('change', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
    showOnlyUnvalidated.addEventListener('change', applyFilters);

    clearFiltersBtn.addEventListener('click', function() {
        searchInput.value = '';
        modelFilter.value = '';
        statusFilter.value = '';
        showOnlyUnvalidated.checked = false;
        renderTable();
    });

    // 13. Mettre à jour les statistiques
    function updateStats() {
        const validated = imagesData.filter(img => img.isValidated).length;
        const total = imagesData.length;
        const percentage = total > 0 ? (validated / total) * 100 : 0;

        validatedCount.textContent = validated;
        totalCount.textContent = total;
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
    }

    // Utilitaires
    function mapModelKey(frontendKey) {
        const mapping = {
            'salesforce_blip': 'salesforce',
            'florence2': 'florence2',
            'git_large': 'git_large'
        };
        return mapping[frontendKey];
    }

    function truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    function showError(message) {
        const errorSection = document.getElementById('errorSection');
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
        errorSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showNotification(message, type = 'info') {
        const alertClass = type === 'success' ? 'alert-success' :
                          type === 'error' ? 'alert-danger' : 'alert-info';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    function attachEventListeners() {
        // Déjà géré dans les sections précédentes
    }

    // Initialiser au chargement
    init();
});