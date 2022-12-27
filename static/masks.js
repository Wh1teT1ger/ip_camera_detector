var canvas = document.getElementById("canvas1");
var ctx = canvas.getContext("2d");
var img = document.getElementById("source");
ctx.drawImage(img, 0, 0);
var mask = []
var masks = []

var buttonAdd = document.getElementById("add");
var buttonStop = document.getElementById("stop");

buttonStop.onclick = function () {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4 && xhr.status == 200) {
            // alert(xhr.responseText);
        }
    }
    xhr.open("POST", "/check_masks/");
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({"masks": masks}));
//setTimeout(() => { console.log("мир"); }, 3000);
    window.location.href = '/camera'

};

buttonAdd.onclick = function () {
    window.ctx.beginPath();
    window.ctx.fillStyle = "red";
    window.ctx.moveTo(window.mask.at(-1).x, window.mask.at(-1).y)
    window.ctx.lineTo(window.mask.at(0).x, window.mask.at(0).y);
    window.ctx.stroke();

    window.masks.push(window.mask)
    window.mask = []


};

function getMousePosition(canvas, event) {
    var rect = canvas.getBoundingClientRect();
    return {
        x: event.clientX - Math.trunc(rect.left),
        y: event.clientY - Math.trunc(rect.top)
    };
}


canvas.addEventListener("mousedown", function (e) {
    var mousePos = getMousePosition(canvas, e);
    window.ctx.beginPath();
    window.ctx.fillStyle = "red";
    window.ctx.fillRect(mousePos.x, mousePos.y, 5, 5);
    window.ctx.fill();
    if (window.mask.length >= 1) {
        window.ctx.beginPath();
        window.ctx.fillStyle = "red";
        window.ctx.moveTo(window.mask.at(-1).x, window.mask.at(-1).y)
        window.ctx.lineTo(mousePos.x, mousePos.y);
        window.ctx.stroke();
    }
    window.mask.push(mousePos)
});