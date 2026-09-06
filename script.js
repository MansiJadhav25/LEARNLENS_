function chooseRole(role) {

    if (role === "teacher") {

        window.location.href = "teacher-dashboard.html";

    }

    else if (role === "student") {

        alert(
            "Welcome, Young Scholar! 🎓\n\n" +
            "Student Dashboard is coming next."
        );

    }

}