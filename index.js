const express = require('express')
const app = express()

app.get("/remote-desktop", (req, res) => {
    res.sendFile(__dirname + "/remote-desktop.html");
})

app.listen(9001)