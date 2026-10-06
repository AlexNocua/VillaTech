
(function () {
    "use strict";

    var uploaders = document.querySelectorAll("[data-file-uploader]");

    var allowedExtensions = new Set([
        "stl",
        "obj",
        "3mf",
        "step",
        "stp",
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "webp"
    ]);

    var maximumFiles = 5;
    var maximumFileSize = 15 * 1024 * 1024;
    var maximumTotalSize = 40 * 1024 * 1024;

    function getExtension(fileName) {
        var pieces = String(fileName).split(".");
        return pieces.length > 1
            ? pieces.pop().toLowerCase()
            : "";
    }

    function getFileKey(file) {
        return [
            file.name,
            file.size,
            file.lastModified
        ].join(":");
    }

    function formatSize(bytes) {
        if (bytes < 1024 * 1024) {
            return Math.max(1, Math.round(bytes / 1024)) + " KB";
        }

        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    uploaders.forEach(function (uploader) {
        var input = uploader.querySelector("[data-file-input]");
        var dropzone = uploader.querySelector("[data-file-dropzone]");
        var selection = uploader.querySelector("[data-file-selection]");
        var list = uploader.querySelector("[data-file-list]");
        var count = uploader.querySelector("[data-file-count]");
        var clearButton = uploader.querySelector("[data-file-clear]");
        var error = uploader.querySelector("[data-file-error]");

        var selectedFiles = [];
        var dragDepth = 0;

        if (!input || !dropzone || !list) {
            return;
        }

        function showError(message) {
            if (!error) {
                return;
            }

            error.textContent = message;
            error.hidden = !message;
        }

        function synchronizeInput() {
            var transfer = new DataTransfer();

            selectedFiles.forEach(function (file) {
                transfer.items.add(file);
            });

            input.files = transfer.files;
        }

        function createFileItem(file) {
            var extension = getExtension(file.name);

            var item = document.createElement("li");
            item.className = "upload-file";

            var type = document.createElement("span");
            type.className = "upload-file__type";
            type.textContent = extension || "FILE";

            var information = document.createElement("span");
            information.className = "upload-file__information";

            var name = document.createElement("strong");
            name.textContent = file.name;

            var size = document.createElement("span");
            size.textContent = formatSize(file.size);

            information.appendChild(name);
            information.appendChild(size);

            var remove = document.createElement("button");
            remove.className = "upload-file__remove";
            remove.type = "button";
            remove.textContent = "×";
            remove.dataset.fileKey = getFileKey(file);
            remove.setAttribute(
                "aria-label",
                "Quitar archivo " + file.name
            );

            item.appendChild(type);
            item.appendChild(information);
            item.appendChild(remove);

            return item;
        }

        function renderFiles() {
            list.replaceChildren();

            selectedFiles.forEach(function (file) {
                list.appendChild(createFileItem(file));
            });

            var amount = selectedFiles.length;

            if (count) {
                count.textContent = amount === 1
                    ? "1 archivo preparado"
                    : amount + " archivos preparados";
            }

            if (selection) {
                selection.hidden = amount === 0;
            }

            dropzone.classList.toggle(
                "has-files",
                amount > 0
            );
        }

        function addFiles(files) {
            showError("");

            var incomingFiles = Array.from(files);
            var existingKeys = new Set(
                selectedFiles.map(getFileKey)
            );

            var rejectedFormats = [];
            var rejectedSizes = [];

            incomingFiles.forEach(function (file) {
                var extension = getExtension(file.name);
                var key = getFileKey(file);

                if (!allowedExtensions.has(extension)) {
                    rejectedFormats.push(file.name);
                    return;
                }

                if (file.size > maximumFileSize) {
                    rejectedSizes.push(file.name);
                    return;
                }

                if (!existingKeys.has(key)) {
                    selectedFiles.push(file);
                    existingKeys.add(key);
                }
            });

            if (selectedFiles.length > maximumFiles) {
                selectedFiles = selectedFiles.slice(0, maximumFiles);

                showError(
                    "Puedes adjuntar un máximo de " +
                    maximumFiles +
                    " archivos."
                );
            }

            var totalSize = selectedFiles.reduce(
                function (total, file) {
                    return total + file.size;
                },
                0
            );

            if (totalSize > maximumTotalSize) {
                selectedFiles = [];

                showError(
                    "El tamaño total de los archivos no puede " +
                    "superar los 40 MB."
                );
            } else if (rejectedSizes.length) {
                showError(
                    "Algunos archivos superan el límite de 15 MB: " +
                    rejectedSizes.join(", ")
                );
            } else if (rejectedFormats.length) {
                showError(
                    "Formato no permitido: " +
                    rejectedFormats.join(", ")
                );
            }

            synchronizeInput();
            renderFiles();
        }

        input.addEventListener("change", function () {
            addFiles(input.files);
        });

        dropzone.addEventListener("dragenter", function (event) {
            event.preventDefault();
            dragDepth += 1;
            dropzone.classList.add("is-dragging");
        });

        dropzone.addEventListener("dragover", function (event) {
            event.preventDefault();

            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = "copy";
            }
        });

        dropzone.addEventListener("dragleave", function (event) {
            event.preventDefault();
            dragDepth -= 1;

            if (dragDepth <= 0) {
                dragDepth = 0;
                dropzone.classList.remove("is-dragging");
            }
        });

        dropzone.addEventListener("drop", function (event) {
            event.preventDefault();

            dragDepth = 0;
            dropzone.classList.remove("is-dragging");

            if (event.dataTransfer) {
                addFiles(event.dataTransfer.files);
            }
        });

        list.addEventListener("click", function (event) {
            var button = event.target.closest(
                ".upload-file__remove"
            );

            if (!button) {
                return;
            }

            selectedFiles = selectedFiles.filter(
                function (file) {
                    return getFileKey(file) !==
                        button.dataset.fileKey;
                }
            );

            showError("");
            synchronizeInput();
            renderFiles();
        });

        if (clearButton) {
            clearButton.addEventListener("click", function () {
                selectedFiles = [];
                showError("");
                synchronizeInput();
                renderFiles();
            });
        }

        var form = uploader.closest("form");

        if (form) {
            form.addEventListener("reset", function () {
                selectedFiles = [];
                showError("");

                window.setTimeout(function () {
                    synchronizeInput();
                    renderFiles();
                }, 0);
            });
        }

        renderFiles();
    });
}());