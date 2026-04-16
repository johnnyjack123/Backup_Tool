import { renderBackupCards } from './index.js';


const socket = io();

socket.on('connect', () => {
    socket.emit('request_backup_state');
    console.log("Connected")
});

socket.on('available_backup_processes', (data) => {
    console.log("Received backup.")
    renderBackupCards(data.backup_paths || []);
});