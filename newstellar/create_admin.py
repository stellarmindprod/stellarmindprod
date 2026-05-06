import os

with open('templates/teacher_marks.html', 'r', encoding='utf-8') as f:
    tech_marks = f.read()

new_marks = tech_marks.replace('data-all-assigned-courses="{{ all_assigned_courses_json | safe }}"', 'data-all-assigned-courses="{{ all_courses_json | safe }}"')
new_marks = new_marks.replace('Teacher Portal — Manage Marks', 'Admin Portal — Manage Marks')
new_marks = new_marks.replace('id="teacherName">Teacher Marks Portal', 'id="teacherName">Admin Marks Portal')

with open('templates/admin_marks.html', 'w', encoding='utf-8') as f:
    f.write(new_marks)

events_html = """{% extends "layout.html" %}
{% block title %}Manage Events{% endblock %}
{% block content %}
<div class="container" style="margin-top: 5rem; text-align: center;">
    <h1>Event Management</h1>
    <p>Coming soon...</p>
</div>
{% endblock %}"""

with open('templates/manage_events.html', 'w', encoding='utf-8') as f:
    f.write(events_html)
