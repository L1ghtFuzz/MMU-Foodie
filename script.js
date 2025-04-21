const parentContainer = document.querySelector('.see-more-container');

parentContainer.addEventListener('click', event=>{
    
    const current = event.target;

    const isSeeMoreBtn = current.className.includes('see-more-btn');

    if(!isSeeMoreBtn) return;

    const currentText = event.target.parentNode.querySelector('.more-category');

    currentText.classList.toggle('more-category--show');

    current.textContent = current.textContent.includes('Show More') ?
    "Show Less" : "Show More";

})

const list = [
    "HTML 5",
    "CSS3",
    "React",
    "PHP",
    "Node.js",
    "JavaScript",
]

const output = document.querySelector('.output');
const search = document.querySelector('.filter-input');

window.addEventListener('DOMContentloaded', loadList);


function loadList(){
    let temp = '<ul class="list-items">'
}