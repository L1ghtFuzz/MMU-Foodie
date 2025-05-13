const list = [
    "HTML 5",
   "CSS3",
   "React",
   "PHP",
   "Node.js",
   "JavaScript",
]

const output = document.querySelector(".output");
const search = document.querySelector(".filter-input");

window.addEventListener("DOMContentLoaded", loadList);

function loadList(){
    let temp = `<ul class="list-items">`;
    list.forEach((item) => {
        temp += `<li class="list-item"> ${item} </li>`;
    });
    temp += `</ul>`;

    if (output) {
    output.innerHTML = temp
    } else {
    console.warn("output element not found");
    }
}