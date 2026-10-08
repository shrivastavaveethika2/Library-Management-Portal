let token = localStorage.getItem("token");

async function register() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    const response = await fetch("/api/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    document.getElementById("authMessage").innerText = data.message;
}


async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    const response = await fetch("/api/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (response.ok) {
        token = data.token;
        localStorage.setItem("token", token);
        document.getElementById("authMessage").innerText =
            "Login successful";
    } else {
        document.getElementById("authMessage").innerText =
            data.message;
    }
}


async function addBook() {
    const book = {
        title: document.getElementById("title").value,
        author: document.getElementById("author").value,
        isbn: document.getElementById("isbn").value,
        category: document.getElementById("category").value
    };

    const response = await fetch("/api/books", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify(book)
    });

    const data = await response.json();

    alert(data.message);
    loadBooks();
}


async function loadBooks() {
    const search = document.getElementById("search").value;

    const response = await fetch(
        "/api/books?search=" + encodeURIComponent(search)
    );

    const books = await response.json();

    const table = document.getElementById("bookTable");

    table.innerHTML = "";

    books.forEach(book => {

        const row = document.createElement("tr");

        const values = [
            book.id,
            book.title,
            book.author,
            book.isbn,
            book.category,
            book.available ? "Available" : "Issued"
        ];

        values.forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        const deleteCell = document.createElement("td");

        const deleteButton = document.createElement("button");
        deleteButton.textContent = "Delete";
        deleteButton.onclick = () => deleteBook(book.id);

        deleteCell.appendChild(deleteButton);
        row.appendChild(deleteCell);

        table.appendChild(row);
    });
}


async function deleteBook(id) {

    const response = await fetch("/api/books/" + id, {
        method: "DELETE",
        headers: {
            "Authorization": "Bearer " + token
        }
    });

    const data = await response.json();

    alert(data.message);

    loadBooks();
}


async function addMember() {

    const member = {
        name: document.getElementById("memberName").value,
        email: document.getElementById("memberEmail").value,
        phone: document.getElementById("memberPhone").value
    };

    const response = await fetch("/api/members", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify(member)
    });

    const data = await response.json();

    alert(data.message);
}


async function issueBook() {

    const bookId = document.getElementById("issueBookId").value;
    const memberId = document.getElementById("issueMemberId").value;

    const response = await fetch("/api/issue", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({
            book_id: bookId,
            member_id: memberId
        })
    });

    const data = await response.json();

    alert(data.message);

    loadBooks();
    loadIssues();
}


async function loadIssues() {

    const response = await fetch("/api/issues");

    const issues = await response.json();

    const table = document.getElementById("issueTable");

    table.innerHTML = "";

    issues.forEach(issue => {

        const row = document.createElement("tr");

        const values = [
            issue.id,
            issue.title,
            issue.name,
            issue.issue_date,
            issue.return_date || "Not Returned"
        ];

        values.forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        const actionCell = document.createElement("td");

        if (issue.return_date) {

            actionCell.textContent = "Returned";

        } else {

            const returnButton = document.createElement("button");

            returnButton.textContent = "Return";

            returnButton.onclick = () => returnBook(issue.id);

            actionCell.appendChild(returnButton);
        }

        row.appendChild(actionCell);

        table.appendChild(row);
    });
}


async function returnBook(id) {

    const response = await fetch("/api/return/" + id, {
        method: "PUT",
        headers: {
            "Authorization": "Bearer " + token
        }
    });

    const data = await response.json();

    alert(data.message);

    loadBooks();
    loadIssues();
}


loadBooks();
loadIssues();