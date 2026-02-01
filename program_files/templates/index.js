
const backupArray = {{ backup_paths | tojson }};
const container = document.getElementById('backupContainer');

// Key Replacement Mapping (kannst du erweitern)
const keyReplacements = {
    'folder_to_backup': 'Folder to save',
    'folder_to_save_backup': 'Folder to store',
    'backup_frequency': 'Backup frequency in hours',
    'last_backup': 'Last Backup',
    'status': 'Status',
    'status_message': 'Status Message',
    'version_history_length': 'Number of max. stored backups'
};

// Backup Karten erzeugen mit keyReplacement
backupArray.forEach(entry => {
    const card = document.createElement('div');
    card.classList.add('col-md-6', 'col-lg-4');
    const cardBody = document.createElement('div');
    cardBody.classList.add('card', 'shadow-sm');

    const header = document.createElement('div');
    header.classList.add('card-header', 'bg-primary', 'text-white', 'fw-bold', 'd-flex', 'justify-content-between', 'align-items-center');

    const titleSpan = document.createElement('span');
    titleSpan.textContent = entry.name ? entry.name : 'Unbenanntes Backup';

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.classList.add('btn', 'btn-danger', 'btn-sm');
    deleteBtn.innerHTML = 'Delete'; // Oder 'Löschen' oder Icon
    deleteBtn.title = 'Delete';
    deleteBtn.addEventListener('click', () => {
        document.getElementById('deleteBackupName').value = entry.name;
        document.getElementById('deleteBackupNameText').textContent = entry.name;

        document.getElementById('deleteBackupId').value = entry.backup_id || '';

        const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        deleteModal.show();
    });

    // innerhalb der backupArray.forEach Schleife, nach deleteBtn
    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.classList.add('btn', 'btn-warning', 'btn-sm', 'm-1'); // Styling
    // Setze den Text je nach Status
    toggleBtn.textContent = (entry.status === 'paused') ? 'Continue' : 'Pause';

    // Event: beim Klick wird Route aufgerufen, Name im hidden input
    toggleBtn.addEventListener('click', () => {
        // Hidden input mit Namen befüllen
        document.getElementById('toggleProcessName').value = entry.name;
        document.getElementById('toggleBackupId').value = entry.backup_id;

        // Formular absenden (z.B. per POST zu /toggle_process)
        document.getElementById('toggleProcessForm').submit();
    });

    header.appendChild(titleSpan);

    header.appendChild(toggleBtn);
    header.appendChild(deleteBtn);

    const ul = document.createElement('ul');
    ul.classList.add('list-group', 'list-group-flush');

    for (const [key, value] of Object.entries(entry)) {
        if (key === 'name') continue;


        const li = document.createElement('li');
        li.classList.add('list-group-item');

        const replacedKey = keyReplacements[key] || key;

        if (key === 'last_backup') {
            li.id = `last_backup-${entry.name}`;
            li.innerHTML = `<strong>${replacedKey}:</strong> <em>Loading...</em>`;
        } else if (key === 'status') {
            // Status Badge mit Farben
            let badgeClass = 'bg-secondary';
            if (value === 'running') badgeClass = 'bg-success';
            else if (value === 'paused') badgeClass = 'bg-warning';
            else if (value === 'stopped') badgeClass = 'bg-danger';

            li.innerHTML = `<strong>${replacedKey}:</strong> <span class="badge ${badgeClass}">${value}</span>`;
        } else if (replacedKey.toLowerCase().includes('status')) {
            // Status-Message Badge
            let badgeClass = (value.toLowerCase() === 'ok') ? 'bg-success' : 'bg-danger';
            li.innerHTML = `<strong>${replacedKey}:</strong> <span class="badge ${badgeClass}">${value}</span>`;
        } else {
            li.innerHTML = `<strong>${replacedKey}:</strong> ${value}`;
        }

        ul.appendChild(li);
    }

    cardBody.appendChild(header);
    cardBody.appendChild(ul);

    // Edit-Button für dieses Backup erzeugen
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.classList.add('btn', 'btn-outline-primary', 'm-3');
    editBtn.textContent = 'Edit';

    // Event Listener mit spezifischem entry
    editBtn.addEventListener('click', () => {
        document.getElementById('editBackupName').value = entry.name;
        document.getElementById('editBackupPath').value = entry.folder_to_backup || '';
        document.getElementById('editBackupSavePath').value = entry.folder_to_save_backup || '';
        document.getElementById('editBackupFrequency').value = entry.backup_frequency || '';
        document.getElementById('originalName').value = entry.name;
        document.getElementById('editStoredVersions').value = entry.version_history_length;

        document.getElementById('editBackupId').value = entry.backup_id || '';

        const editModal = new bootstrap.Modal(document.getElementById('editBackupModal'));
        editModal.show();
    });


    cardBody.appendChild(editBtn);
    card.appendChild(cardBody);
    container.appendChild(card);
});

// Live Validierung für eindeutigen Namen im Formular
const nameInput = document.getElementById('backupName');
const nameError = document.getElementById('nameError');
const submitButton = document.querySelector('form button[type="submit"]');

nameInput.addEventListener('input', () => {
    const enteredName = nameInput.value.trim().toLowerCase();
    const nameExists = backupArray.some(entry => entry.name && entry.name.toLowerCase() === enteredName);

    if (nameExists) {
        nameError.style.display = 'block';
        submitButton.disabled = true;
    } else {
        nameError.style.display = 'none';
        submitButton.disabled = false;
    }
});

// Status update
const socket = io();

socket.on('status_update', (data) => {
    console.log("Status Update:", data);

    // Beispiel: Statusfeld in Backup-Karte aktualisieren (du müsstest pro Backup eine Statusanzeige mit einer ID o.ä. anlegen)
    const statusElement = document.querySelector(`#status-${data.id}`);
    if (statusElement) {
        statusElement.textContent = data.status;
    }
});

// Backup time update
socket.on('backup_time_update', (backupTimes) => {
    console.log("Received backup_time_update:", backupTimes);

    backupTimes.forEach(data => {
        const lastBackupElement = document.getElementById(`last_backup-${data.name}`);
        if (lastBackupElement) {
            lastBackupElement.innerHTML = `<strong>${keyReplacements['last_backup']}:</strong> ${data.last_backup || "<em>Keine Daten</em>"}`;
        }
    });
});