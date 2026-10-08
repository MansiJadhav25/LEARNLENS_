const express = require("express");
const mysql = require("mysql2");

const app = express();

const PORT = 3000;

// MySQL connection
const db = mysql.createConnection({
    host: "localhost",
    user: "root",
    password: "root",
    database: "learnlens"
});

// Connect to MySQL
db.connect((err) => {
    if (err) {
        console.log("❌ MySQL connection failed:");
        console.log(err.message);
        return;
    }

    console.log("✅ MySQL connected successfully!");
});

// Home page
app.get("/", (req, res) => {
    res.send("LearnLens Backend is Running!");
});

// Test API - get all students
app.get("/students", (req, res) => {

    const sql = "SELECT * FROM students";

    db.query(sql, (err, results) => {

        if (err) {
            console.log("❌ Error fetching students:");
            console.log(err.message);

            res.status(500).send("Database error");
            return;
        }

        res.json(results);
    });
});
// Test API - get all marks
app.get("/marks", (req, res) => {

    const sql = `
        SELECT
            students.student_name,
            students.roll_number,
            subjects.subject_name,
            marks.marks_obtained,
            marks.total_marks
        FROM marks
        JOIN students
            ON marks.student_id = students.student_id
        JOIN subjects
            ON marks.subject_id = subjects.subject_id
    `;

    db.query(sql, (err, results) => {

        if (err) {
            console.log("❌ Error fetching marks:");
            console.log(err.message);

            res.status(500).send("Database error");
            return;
        }

        res.json(results);
    });
});

// Start server
app.listen(PORT, () => {
    console.log(
        `LearnLens backend running at http://localhost:${PORT}`
    );
});