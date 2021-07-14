const express = require('express')
const app = express()

app.get("/keyboard", (req, res) => {
    res.sendFile(__dirname + "/keyboard.html");
})

app.get("/remote-desktop", (req, res) => {
    res.sendFile(__dirname + "/remote-desktop.html");
})

app.listen(9001)