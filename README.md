StudySphere — Web-Based Student Study Management System

StudySphere is a full-stack academic web application built with Django and Python. It helps university students manage their study materials, plan their schedules, track exam dates, and test their knowledge using AI-generated quizzes.

Features

Secure user authentication with registration, login, and password reset
Private PDF library — upload, organise, and read textbooks in the browser
Reading progress saved automatically with page bookmarks
Personal study schedule planner with session tracking
Exam date manager with automatic countdown
In-app notification system
AI-powered quiz generator using the Anthropic Claude API — generates multiple-choice questions directly from uploaded PDFs
Full quiz engine with scoring, answer review, and attempt history
Dark and light mode support
Fully responsive on mobile and desktop

Tech Stack

Backend: Django 6, Python
Frontend: HTML, CSS, Bootstrap 5, JavaScript
Database: SQLite
AI: Anthropic Claude API (claude-sonnet-4-6)
PDF Processing: pdfplumber, PDF.js

Setup

Clone the repository
Create and activate a virtual environment
Run pip install django anthropic pdfplumber pillow
Add your Anthropic API key to settings.py as ANTHROPIC_API_KEY
Run python manage.py migrate
Run python manage.py createsuperuser
Run python manage.py runserver
Visit http://127.0.0.1:8000

Developer

Built by Decent — Freelance Web Developer, Awka, Nigeria.
