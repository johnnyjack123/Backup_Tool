const container = document.getElementById('backupContainer');
const socket = io();

let backupArray = [];

const keyReplacements = {
    'folder_to_backup': 'Folder to save',
    'folder_to_save_backup': 'Folder to store',
    'backup_frequency': 'Backup frequency in hours',
    'last_backup': 'Last Backup',
    'status': 'Status',
    'status_message': 'Status Message',
    'version_history_length': 'Number of max. stored backups'
};

function renderBackups(backups) {
    container.innerHTML = '';
    backupArray = backups;

    backups.forEach(entry => {
        const card = document.createElement('div');
        card.classList.add('col-md-6', 'col-lg-4');

        const cardBody = document.createElement('div');
        cardBody.classList.add('card', 'shadow-sm');

        const header = document.createElement('div');
        header.classList.add('card-header', 'bg-primary', 'text-white', 'fw-bold', 'd-flex', 'justify-content-between', 'align-items-center');

        const titleSpan = document.createElement('span');
        titleSpan.textContent = entry.name || 'Unbenanntes Backup';

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.classList.add('btn', 'btn-danger', 'btn-sm');
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', () => {
            document.getElementById('deleteBackupName').value = entry.name;
            document.getElementById('deleteBackupNameText').textContent = entry.name;
            document.getElementById('deleteBackupId').value = entry.backup_id || '';
            new bootstrap.Modal(document.getElementById('deleteConfirmModal')).show();
        });

        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.classList.add('btn', 'btn-warning', 'btn-sm', 'm-1');
        toggleBtn.textContent = (entry.status === 'paused') ? 'Continue' : 'Pause';
        toggleBtn.addEventListener('click', () => {
            socket.emit('toggle_backup', { backup_id: entry.backup_id, name: entry.name });
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

            if (key === 'status') {
                let badgeClass = 'bg-secondary';
                if (value === 'running') badgeClass = 'bg-success';
                else if (value === 'paused') badgeClass = 'bg-warning';
                else if (value === 'stopped') badgeClass = 'bg-danger';

                li.innerHTML = `<strong>${replacedKey}:</strong> <span class="badge ${badgeClass}">${value}</span>`;
            } else if (replacedKey.toLowerCase().includes('status')) {
                const badgeClass = String(value).toLowerCase() === 'ok' ? 'bg-success' : 'bg-danger';
                li.innerHTML = `<strong>${replacedKey}:</strong> <span class="badge ${badgeClass}">${value}</span>`;
            } else {
                li.innerHTML = `<strong>${replacedKey}:</strong> ${value}`;
            }

            ul.appendChild(li);
        }

        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.classList.add('btn', 'btn-outline-primary', 'm-3');
        editBtn.textContent = 'Edit';
        editBtn.addEventListener('click', () => {
            document.getElementById('editBackupName').value = entry.name;
            document.getElementById('editBackupPath').value = entry.folder_to_backup || '';
            document.getElementById('editBackupSavePath').value = entry.folder_to_save_backup || '';
            document.getElementById('editBackupFrequency').value = entry.backup_frequency || '';
            document.getElementById('originalName').value = entry.name;
            document.getElementById('editStoredVersions').value = entry.version_history_length || 0;
            document.getElementById('editBackupId').value = entry.backup_id || '';
            new bootstrap.Modal(document.getElementById('editBackupModal')).show();
        });

        cardBody.appendChild(header);
        cardBody.appendChild(ul);
        cardBody.appendChild(editBtn);
        card.appendChild(cardBody);
        container.appendChild(card);
    });
}

socket.on('connect', () => {
    socket.emit('request_backup_state');
});

socket.on('backup_state', (data) => {
    renderBackups(data.backup_paths || []);
});
