import { renderBackupCards } from './index.js';

const socket = io();

socket.on('connect', () => {
    console.log("Socket connected to server")
});

socket.on('available_backup_processes', (data) => {
    console.log("Received backup.")
    renderBackupCards(data || []);
    console.log(data)
});