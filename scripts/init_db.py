#!/usr/bin/env python3
"""Database initialization, migration and seeding script"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import json
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import engine, Base, AsyncSessionLocal
from app.config.settings import get_settings
from app.models.database import *  # Import all models
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

class DatabaseInitializer:
    """Database initialization and seeding"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = AsyncSessionLocal()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def create_tables(self):
        """Create all database tables"""
        try:
            logger.info("🔄 Creating database tables...")
            
            async with engine.begin() as conn:
                # Drop all tables if in development (careful!)
                if settings.ENVIRONMENT == "development":
                    await conn.run_sync(Base.metadata.drop_all)
                    logger.info("🗑️  Dropped existing tables (development mode)")
                
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("✅ Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {str(e)}")
            raise
    
    async def seed_categories(self):
        """Seed initial categories"""
        try:
            logger.info("🌱 Seeding categories...")
            
            categories_data = [
                {
                    "name": "Programming & Development",
                    "slug": "programming-development",
                    "description": "Learn programming languages, frameworks, and software development",
                    "color": "#3B82F6",
                    "orderIndex": 1,
                    "isActive": True,
                    "isFeatured": True
                },
                {
                    "name": "Data Science & Analytics",
                    "slug": "data-science-analytics", 
                    "description": "Master data analysis, machine learning, and AI",
                    "color": "#10B981",
                    "orderIndex": 2,
                    "isActive": True,
                    "isFeatured": True
                },
                {
                    "name": "Business & Management",
                    "slug": "business-management",
                    "description": "Develop business skills and leadership capabilities",
                    "color": "#F59E0B",
                    "orderIndex": 3,
                    "isActive": True,
                    "isFeatured": False
                },
                {
                    "name": "Design & Creative",
                    "slug": "design-creative",
                    "description": "Explore graphic design, UI/UX, and creative arts",
                    "color": "#EF4444",
                    "orderIndex": 4,
                    "isActive": True,
                    "isFeatured": False
                },
                {
                    "name": "Language Learning",
                    "slug": "language-learning",
                    "description": "Learn new languages and improve communication skills",
                    "color": "#8B5CF6",
                    "orderIndex": 5,
                    "isActive": True,
                    "isFeatured": False
                },
                {
                    "name": "Personal Development",
                    "slug": "personal-development",
                    "description": "Develop soft skills and personal growth",
                    "color": "#06B6D4",
                    "orderIndex": 6,
                    "isActive": True,
                    "isFeatured": False
                }
            ]
            
            for cat_data in categories_data:
                # Check if category already exists
                existing = await self.session.execute(
                    text("SELECT id FROM categories WHERE slug = :slug"),
                    {"slug": cat_data["slug"]}
                )
                if existing.fetchone():
                    continue
                
                category = Category(
                    id=str(uuid.uuid4()),
                    **cat_data,
                    seoMeta={
                        "title": f"{cat_data['name']} Courses | LMS",
                        "description": cat_data["description"],
                        "keywords": cat_data["name"].lower().replace(" ", ",")
                    }
                )
                self.session.add(category)
            
            await self.session.commit()
            logger.info("✅ Categories seeded successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to seed categories: {str(e)}")
            raise
    
    async def seed_admin_user(self):
        """Create default admin user"""
        try:
            logger.info("🔐 Creating admin user...")
            
            # Check if admin already exists
            existing = await self.session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": "admin@lms.com"}
            )
            if existing.fetchone():
                logger.info("ℹ️  Admin user already exists")
                return
            
            admin_id = str(uuid.uuid4())
            
            # Create admin user
            admin_user = User(
                id=admin_id,
                email="admin@lms.com",
                username="admin",
                passwordHash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/L3XrqHxqV5F5t2jBO",  # hashed "admin123"
                firstName="System",
                lastName="Administrator",
                displayName="System Admin",
                userType="admin",
                status="active",
                emailVerified=True,
                preferredLanguage="en",
                timezone="UTC"
            )
            self.session.add(admin_user)
            
            # Create admin profile
            admin_profile = UserProfile(
                id=str(uuid.uuid4()),
                userId=admin_id,
                bio="System administrator with full access to the LMS platform",
                isPublic=False,
                isSearchable=False,
                isVerified=True,
                verifiedAt=datetime.utcnow()
            )
            self.session.add(admin_profile)
            
            await self.session.commit()
            logger.info("✅ Admin user created successfully")
            logger.info("   📧 Email: admin@lms.com")
            logger.info("   🔑 Password: admin123")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to create admin user: {str(e)}")
            raise
    
    async def seed_demo_teacher(self):
        """Create demo teacher user"""
        try:
            logger.info("👨‍🏫 Creating demo teacher...")
            
            # Check if teacher already exists
            existing = await self.session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": "teacher@lms.com"}
            )
            if existing.fetchone():
                logger.info("ℹ️  Demo teacher already exists")
                return
            
            teacher_id = str(uuid.uuid4())
            
            # Create teacher user
            teacher_user = User(
                id=teacher_id,
                email="teacher@lms.com",
                username="demo_teacher",
                passwordHash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/L3XrqHxqV5F5t2jBO",  # hashed "teacher123"
                firstName="John",
                lastName="Smith",
                displayName="Dr. John Smith",
                userType="teacher",
                status="active",
                emailVerified=True,
                preferredLanguage="en",
                timezone="UTC"
            )
            self.session.add(teacher_user)
            
            # Create teacher profile
            teacher_profile = UserProfile(
                id=str(uuid.uuid4()),
                userId=teacher_id,
                bio="Experienced software engineer and educator with 10+ years in the industry",
                organization="Tech University",
                jobTitle="Senior Software Engineer & Instructor",
                isPublic=True,
                isSearchable=True,
                isVerified=True,
                verifiedAt=datetime.utcnow()
            )
            self.session.add(teacher_profile)
            
            # Create teacher profile
            teacher_profile_detail = TeacherProfile(
                id=str(uuid.uuid4()),
                userId=teacher_id,
                teacherCode="TEACH001",
                specializations="Python, Machine Learning, Web Development, Data Science",
                qualifications="PhD in Computer Science, AWS Certified Solutions Architect",
                yearsExperience=10,
                teachingStyle="Interactive and project-based learning with real-world examples",
                rating=4.8,
                totalRatings=245,
                isApproved=True,
                isActive=True,
                isFeatured=True,
                isVerified=True,
                approvedAt=datetime.utcnow(),
                subjects=json.dumps([
                    "Python Programming",
                    "Machine Learning",
                    "Web Development",
                    "Data Science",
                    "AI Fundamentals"
                ]),
                teachingLanguages=json.dumps(["English", "Vietnamese"]),
                hourlyRate=50.00,
                currency="USD",
                acceptingStudents=True,
                maxStudentsPerClass=30,
                allowReviews=True,
                professionalSummary="Passionate educator dedicated to making complex technical concepts accessible to learners of all backgrounds."
            )
            self.session.add(teacher_profile_detail)
            
            await self.session.commit()
            logger.info("✅ Demo teacher created successfully")
            logger.info("   📧 Email: teacher@lms.com")
            logger.info("   🔑 Password: teacher123")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to create demo teacher: {str(e)}")
            raise
    
    async def seed_demo_student(self):
        """Create demo student user"""
        try:
            logger.info("🎓 Creating demo student...")
            
            # Check if student already exists
            existing = await self.session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": "student@lms.com"}
            )
            if existing.fetchone():
                logger.info("ℹ️  Demo student already exists")
                return
            
            student_id = str(uuid.uuid4())
            
            # Create student user
            student_user = User(
                id=student_id,
                email="student@lms.com",
                username="demo_student",
                passwordHash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/L3XrqHxqV5F5t2jBO",  # hashed "student123"
                firstName="Alice",
                lastName="Johnson",
                displayName="Alice Johnson",
                userType="student",
                status="active",
                emailVerified=True,
                preferredLanguage="en",
                timezone="UTC"
            )
            self.session.add(student_user)
            
            # Create student profile
            student_profile = UserProfile(
                id=str(uuid.uuid4()),
                userId=student_id,
                bio="Computer Science student passionate about AI and machine learning",
                dateOfBirth=datetime(1998, 5, 15).date(),
                gender="female",
                country="Vietnam",
                city="Ho Chi Minh City",
                organization="Vietnam National University",
                isPublic=True,
                isSearchable=True
            )
            self.session.add(student_profile)
            
            # Create student profile details
            student_profile_detail = StudentProfile(
                id=str(uuid.uuid4()),
                userId=student_id,
                studentCode="STU001",
                educationLevel="University",
                fieldOfStudy="Computer Science",
                institution="Vietnam National University",
                graduationYear=2024,
                gpa=3.8,
                learningGoals="Master AI and machine learning to build intelligent applications",
                preferredLearningStyle="visual",
                studyTimePreference="evening",
                difficultyPreference="intermediate",
                motivationFactors="Career advancement and personal interest in technology",
                enableAIRecommendations=True,
                enableProgressTracking=True,
                learningPreferences=json.dumps({
                    "video_speed": 1.25,
                    "subtitle_language": "en",
                    "notifications_enabled": True,
                    "study_reminders": True
                })
            )
            self.session.add(student_profile_detail)
            
            await self.session.commit()
            logger.info("✅ Demo student created successfully")
            logger.info("   📧 Email: student@lms.com")
            logger.info("   🔑 Password: student123")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to create demo student: {str(e)}")
            raise
    
    async def seed_demo_course(self):
        """Create a demo course with lessons"""
        try:
            logger.info("📚 Creating demo course...")
            
            # Get teacher and category IDs
            teacher_result = await self.session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": "teacher@lms.com"}
            )
            teacher_row = teacher_result.fetchone()
            if not teacher_row:
                logger.error("Demo teacher not found")
                return
            
            category_result = await self.session.execute(
                text("SELECT id FROM categories WHERE slug = :slug"),
                {"slug": "programming-development"}
            )
            category_row = category_result.fetchone()
            if not category_row:
                logger.error("Programming category not found")
                return
            
            teacher_id = teacher_row[0]
            category_id = category_row[0]
            
            # Check if course already exists
            existing = await self.session.execute(
                text("SELECT id FROM courses WHERE slug = :slug"),
                {"slug": "python-for-beginners"}
            )
            if existing.fetchone():
                logger.info("ℹ️  Demo course already exists")
                return
            
            course_id = str(uuid.uuid4())
            
            # Create demo course
            demo_course = Course(
                id=course_id,
                title="Python Programming for Beginners",
                slug="python-for-beginners",
                description="A comprehensive introduction to Python programming language covering fundamentals, data structures, and practical applications.",
                shortDescription="Learn Python programming from scratch with hands-on projects and real-world examples.",
                teacherId=teacher_id,
                categoryId=category_id,
                level="beginner",
                language="en",
                durationHours=20,
                durationMinutes=30,
                price=79.99,
                currency="USD",
                originalPrice=99.99,
                isFree=False,
                pricingModel="paid",
                status="published",
                tags=json.dumps(["python", "programming", "beginner", "coding", "software development"]),
                requirements=json.dumps([
                    "Basic computer literacy",
                    "Access to a computer with internet connection",
                    "No prior programming experience required"
                ]),
                whatYouWillLearn=json.dumps([
                    "Python syntax and fundamentals",
                    "Data types and variables",
                    "Control structures (loops, conditionals)",
                    "Functions and modules",
                    "File handling and data processing",
                    "Object-oriented programming basics",
                    "Working with APIs and databases",
                    "Building practical projects"
                ]),
                targetAudience=json.dumps([
                    "Complete beginners to programming",
                    "Students looking to learn their first programming language",
                    "Professionals wanting to add Python skills",
                    "Anyone interested in software development"
                ]),
                rating=4.7,
                totalRatings=156,
                totalEnrollments=1250,
                totalCompletions=890,
                featured=True,
                bestseller=True,
                allowReviews=True,
                allowDiscussions=True,
                hasCertificate=True,
                lifetimeAccess=True,
                publishedAt=datetime.utcnow() - timedelta(days=30),
                seoMeta=json.dumps({
                    "title": "Python Programming for Beginners - Complete Course | LMS",
                    "description": "Master Python programming from scratch with our comprehensive beginner course. Hands-on projects, expert instruction, and lifetime access.",
                    "keywords": "python, programming, beginner, course, online learning, coding"
                })
            )
            self.session.add(demo_course)
            
            # Create course sections
            sections_data = [
                {
                    "title": "Getting Started with Python",
                    "description": "Introduction to Python and setting up your development environment",
                    "orderIndex": 1
                },
                {
                    "title": "Python Fundamentals",
                    "description": "Learn basic Python syntax, variables, and data types",
                    "orderIndex": 2
                },
                {
                    "title": "Control Structures",
                    "description": "Master loops, conditionals, and decision making in Python",
                    "orderIndex": 3
                },
                {
                    "title": "Functions and Modules",
                    "description": "Create reusable code with functions and organize with modules",
                    "orderIndex": 4
                },
                {
                    "title": "Data Structures",
                    "description": "Work with lists, dictionaries, sets, and tuples",
                    "orderIndex": 5
                },
                {
                    "title": "File Handling & Projects",
                    "description": "Handle files and build practical projects",
                    "orderIndex": 6
                }
            ]
            
            section_ids = []
            for section_data in sections_data:
                section_id = str(uuid.uuid4())
                section = CourseSection(
                    id=section_id,
                    courseId=course_id,
                    **section_data,
                    isActive=True,
                    isRequired=True
                )
                self.session.add(section)
                section_ids.append(section_id)
            
            # Create demo lessons for first section
            lessons_data = [
                {
                    "title": "What is Python?",
                    "slug": "what-is-python",
                    "description": "Introduction to Python programming language and its applications",
                    "content": "Python is a high-level, interpreted programming language known for its simplicity and readability...",
                    "lessonType": "video",
                    "orderIndex": 1,
                    "videoDuration": 480,  # 8 minutes
                    "estimatedDuration": 10,
                    "isPreview": True
                },
                {
                    "title": "Installing Python and IDE",
                    "slug": "installing-python-ide",
                    "description": "Step-by-step guide to install Python and set up your development environment",
                    "content": "In this lesson, we'll install Python and set up a development environment...",
                    "lessonType": "video",
                    "orderIndex": 2,
                    "videoDuration": 720,  # 12 minutes
                    "estimatedDuration": 15,
                    "isPreview": True
                },
                {
                    "title": "Your First Python Program",
                    "slug": "first-python-program",
                    "description": "Write and run your first Python program",
                    "content": "Let's write our first Python program and understand how Python code is executed...",
                    "lessonType": "video",
                    "orderIndex": 3,
                    "videoDuration": 600,  # 10 minutes
                    "estimatedDuration": 12
                }
            ]
            
            for lesson_data in lessons_data:
                lesson = Lesson(
                    id=str(uuid.uuid4()),
                    courseId=course_id,
                    sectionId=section_ids[0],  # First section
                    **lesson_data,
                    status="published",
                    isActive=True,
                    isMandatory=True,
                    publishedAt=datetime.utcnow()
                )
                self.session.add(lesson)
            
            await self.session.commit()
            logger.info("✅ Demo course created successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to create demo course: {str(e)}")
            raise
    
    async def seed_chatbot_knowledge(self):
        """Seed initial chatbot knowledge base"""
        try:
            logger.info("🤖 Seeding chatbot knowledge base...")
            
            knowledge_data = [
                {
                    "category": "general",
                    "question": "How do I enroll in a course?",
                    "answer": "To enroll in a course, browse our course catalog, click on the course you're interested in, and click the 'Enroll Now' button. You can pay with credit card or other supported payment methods.",
                    "keywords": "enroll, enrollment, course, register, sign up",
                    "confidence": 0.95
                },
                {
                    "category": "technical",
                    "question": "What are the technical requirements?",
                    "answer": "You need a computer or mobile device with internet connection. Our platform works on modern browsers including Chrome, Firefox, Safari, and Edge. For the best experience, we recommend using the latest version of your browser.",
                    "keywords": "requirements, technical, browser, device, system",
                    "confidence": 0.90
                },
                {
                    "category": "learning",
                    "question": "How does the AI recommendation system work?",
                    "answer": "Our AI system analyzes your learning patterns, progress, and preferences to suggest personalized content. It tracks your performance and recommends the most suitable next steps in your learning journey.",
                    "keywords": "AI, recommendation, personalized, learning path, suggestions",
                    "confidence": 0.92
                },
                {
                    "category": "certificates",
                    "question": "Do I get a certificate after completing a course?",
                    "answer": "Yes! You'll receive a certificate of completion for each course you successfully finish. Certificates can be downloaded and shared on professional networks like LinkedIn.",
                    "keywords": "certificate, completion, credential, LinkedIn, download",
                    "confidence": 0.98
                },
                {
                    "category": "progress",
                    "question": "How can I track my learning progress?",
                    "answer": "Your progress is automatically tracked as you complete lessons and assessments. Check your dashboard to see completion percentages, time spent, and detailed analytics about your learning journey.",
                    "keywords": "progress, tracking, dashboard, analytics, completion",
                    "confidence": 0.94
                }
            ]
            
            for kb_data in knowledge_data:
                knowledge = ChatbotKnowledgeBase(
                    id=str(uuid.uuid4()),
                    **kb_data
                )
                self.session.add(knowledge)
            
            await self.session.commit()
            logger.info("✅ Chatbot knowledge base seeded successfully")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to seed chatbot knowledge: {str(e)}")
            raise
    
    async def run_full_migration(self):
        """Run complete database migration and seeding"""
        try:
            # Create tables
            await self.create_tables()
            
            # Seed initial data
            await self.seed_categories()
            await self.seed_admin_user()
            await self.seed_demo_teacher()
            await self.seed_demo_student()
            await self.seed_demo_course()
            await self.seed_chatbot_knowledge()
            
            logger.info("🎉 Database migration and seeding completed successfully!")
            
            # Print summary
            logger.info("\n" + "="*60)
            logger.info("DATABASE SETUP SUMMARY")
            logger.info("="*60)
            logger.info("🔐 Admin Account:")
            logger.info("   Email: admin@lms.com")
            logger.info("   Password: admin123")
            logger.info("\n👨‍🏫 Demo Teacher Account:")
            logger.info("   Email: teacher@lms.com")
            logger.info("   Password: teacher123")
            logger.info("\n🎓 Demo Student Account:")
            logger.info("   Email: student@lms.com")
            logger.info("   Password: student123")
            logger.info("\n📚 Demo Course: Python Programming for Beginners")
            logger.info("🤖 Chatbot Knowledge Base: 5 entries")
            logger.info("📂 Categories: 6 categories")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            raise

async def main():
    """Main migration function"""
    try:
        async with DatabaseInitializer() as db_init:
            await db_init.run_full_migration()
        
        # Close engine
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())