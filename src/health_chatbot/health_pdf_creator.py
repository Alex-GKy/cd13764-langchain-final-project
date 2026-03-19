from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import os

def create_health_pdfs():
    """Create comprehensive PDF documents for common health issues"""
    
    topics = [
        "Tension Headaches: Causes, Symptoms, and Treatment",
        "Lower Back Pain: Prevention and Management", 
        "Understanding Migraines: Triggers and Relief",
        "Neck Pain: Common Causes and Solutions",
        "Stress Management for Pain Relief"
    ]
    
    # Health content data
    health_content = {
        "Tension Headaches: Causes, Symptoms, and Treatment": {
            "introduction": """
            Tension headaches are the most common type of headache, affecting millions of people worldwide. 
            These headaches are characterized by a dull, aching sensation that feels like a tight band around 
            the head. Unlike migraines, tension headaches typically don't cause severe disability, but they 
            can significantly impact daily activities and quality of life.
            """,
            "causes": [
                "Stress and anxiety - emotional tension is a primary trigger",
                "Muscle tension in the neck, shoulders, and scalp",
                "Poor posture, especially during computer work",
                "Eye strain from prolonged screen time or reading",
                "Dehydration and irregular eating patterns",
                "Lack of sleep or changes in sleep patterns",
                "Environmental factors like bright lights or loud noises",
                "Certain foods and food additives",
                "Hormonal changes, particularly in women"
            ],
            "symptoms": [
                "Dull, aching head pain that may feel like pressure",
                "Sensation of tightness or pressure across forehead or sides of head",
                "Tenderness in scalp, neck, and shoulder muscles",
                "Pain is typically bilateral (affects both sides of the head)",
                "Mild to moderate intensity that doesn't worsen with activity",
                "No nausea or vomiting (unlike migraines)",
                "Possible sensitivity to light or sound, but not both",
                "Duration can range from 30 minutes to several days"
            ],
            "prevention": [
                "Maintain regular sleep schedule - aim for 7-9 hours nightly",
                "Practice stress management techniques like deep breathing",
                "Take regular breaks during computer work (20-20-20 rule)",
                "Maintain good posture throughout the day",
                "Stay hydrated by drinking adequate water daily",
                "Exercise regularly to reduce muscle tension",
                "Limit caffeine intake and avoid excessive alcohol",
                "Create a comfortable work environment with proper lighting",
                "Consider ergonomic adjustments to workspace"
            ],
            "treatment": [
                "Over-the-counter pain relievers: acetaminophen, ibuprofen, aspirin",
                "Apply heat or cold therapy to head, neck, or shoulders",
                "Gentle massage of temples, neck, and shoulder muscles",
                "Relaxation techniques: progressive muscle relaxation, meditation",
                "Adequate rest in a quiet, dark room",
                "Stay hydrated and eat regular, balanced meals",
                "Gentle stretching exercises for neck and shoulders",
                "Prescription medications for frequent headaches",
                "Preventive medications if headaches occur more than twice weekly"
            ]
        },
        
        "Lower Back Pain: Prevention and Management": {
            "introduction": """
            Lower back pain is one of the most common medical complaints, affecting up to 80% of adults 
            at some point in their lives. It can range from a dull, constant ache to sudden, sharp pain 
            that makes movement difficult. Most lower back pain is acute, lasting a few days to weeks, 
            but it can become chronic if not properly addressed.
            """,
            "causes": [
                "Muscle or ligament strain from heavy lifting or sudden movements",
                "Herniated or bulging discs pressing on nerves",
                "Arthritis affecting the lower back joints",
                "Skeletal irregularities like scoliosis",
                "Osteoporosis causing vertebral fractures",
                "Poor posture during sitting, standing, or sleeping",
                "Sedentary lifestyle leading to weak core muscles",
                "Obesity putting extra stress on the spine",
                "Age-related wear and tear on spinal structures"
            ],
            "symptoms": [
                "Dull aching or sharp pain in the lower back",
                "Pain that radiates down one or both legs (sciatica)",
                "Muscle spasms in the back or hip area",
                "Stiffness and reduced range of motion",
                "Pain that worsens with sitting or bending forward",
                "Difficulty standing up straight after sitting",
                "Pain that improves with walking or changing positions",
                "Numbness or tingling in legs or feet",
                "Weakness in leg muscles in severe cases"
            ],
            "prevention": [
                "Maintain good posture while sitting, standing, and walking",
                "Strengthen core muscles through regular exercise",
                "Use proper lifting techniques - lift with legs, not back",
                "Maintain a healthy weight to reduce spinal stress",
                "Sleep on a supportive mattress with proper pillow placement",
                "Take frequent breaks from prolonged sitting",
                "Wear comfortable, low-heeled shoes",
                "Set up an ergonomic workspace",
                "Stay active with regular low-impact exercise"
            ],
            "treatment": [
                "Rest for short periods, but avoid prolonged bed rest",
                "Apply ice for first 24-48 hours, then switch to heat",
                "Over-the-counter pain medications: NSAIDs, acetaminophen",
                "Gentle stretching and movement as tolerated",
                "Physical therapy to strengthen muscles and improve flexibility",
                "Massage therapy to reduce muscle tension",
                "Gradual return to normal activities",
                "Prescription medications for severe pain",
                "Epidural injections for nerve-related pain"
            ]
        },
        
        "Understanding Migraines: Triggers and Relief": {
            "introduction": """
            Migraines are intense, debilitating headaches that affect over 39 million Americans. 
            They are a neurological condition that goes far beyond a typical headache, often 
            accompanied by nausea, sensitivity to light and sound, and can last from hours to days. 
            Understanding migraine triggers and effective treatment strategies is crucial for managing 
            this complex condition.
            """,
            "causes": [
                "Genetic predisposition - family history increases risk",
                "Hormonal changes, especially in women during menstruation",
                "Certain foods: aged cheese, chocolate, MSG, processed meats",
                "Stress and emotional triggers",
                "Changes in sleep patterns or irregular sleep",
                "Weather changes and barometric pressure fluctuations",
                "Strong smells, bright lights, or loud sounds",
                "Dehydration and skipping meals",
                "Alcohol, particularly red wine and beer"
            ],
            "symptoms": [
                "Severe, throbbing pain usually on one side of head",
                "Nausea and vomiting",
                "Extreme sensitivity to light (photophobia)",
                "Extreme sensitivity to sound (phonophobia)",
                "Visual disturbances or aura before headache",
                "Dizziness and lightheadedness",
                "Fatigue and difficulty concentrating",
                "Neck stiffness and muscle tension",
                "Symptoms can last 4-72 hours if untreated"
            ],
            "prevention": [
                "Identify and avoid personal triggers through headache diary",
                "Maintain regular sleep schedule",
                "Eat regular, balanced meals - don't skip meals",
                "Stay hydrated throughout the day",
                "Manage stress through relaxation techniques",
                "Limit exposure to known triggers like certain foods",
                "Exercise regularly but avoid sudden intense activity",
                "Consider preventive medications if migraines are frequent",
                "Create a calm, comfortable environment at home and work"
            ],
            "treatment": [
                "Early intervention with triptan medications",
                "Over-the-counter options: ibuprofen, naproxen, acetaminophen",
                "Rest in a quiet, dark room",
                "Apply cold compress to head or warm compress to neck",
                "Stay hydrated with small sips of water",
                "Anti-nausea medications if needed",
                "Prescription preventive medications for frequent migraines",
                "CGRP inhibitors for prevention and treatment",
                "Alternative therapies: acupuncture, biofeedback"
            ]
        },
        
        "Neck Pain: Common Causes and Solutions": {
            "introduction": """
            Neck pain is a common complaint that can result from various causes, ranging from 
            poor posture to more serious underlying conditions. The neck, or cervical spine, 
            supports the weight of the head and allows for a wide range of motion, making it 
            vulnerable to injury and pain. Most neck pain is not serious and can be resolved 
            with proper care and treatment.
            """,
            "causes": [
                "Poor posture from prolonged computer use or phone use",
                "Sleeping in awkward positions or with poor pillow support",
                "Muscle strain from sudden movements or overuse",
                "Whiplash from car accidents or sports injuries",
                "Herniated cervical disc pressing on nerves",
                "Arthritis affecting the cervical spine joints",
                "Pinched nerves in the neck region",
                "Stress causing muscle tension in neck and shoulders",
                "Age-related wear and tear of cervical vertebrae"
            ],
            "symptoms": [
                "Pain and stiffness in the neck area",
                "Pain that radiates to shoulders, arms, or upper back",
                "Headaches, particularly at the base of the skull",
                "Reduced range of motion in the neck",
                "Muscle spasms in the neck and shoulder area",
                "Numbness or tingling in arms or hands",
                "Weakness in arms or hands in severe cases",
                "Grinding sensation when moving the neck",
                "Sharp or burning pain with certain movements"
            ],
            "prevention": [
                "Maintain proper posture while sitting and standing",
                "Adjust computer monitor to eye level",
                "Use ergonomic support for neck during computer work",
                "Sleep with proper pillow support for neck alignment",
                "Take frequent breaks from desk work to stretch",
                "Strengthen neck and shoulder muscles through exercise",
                "Avoid carrying heavy bags on one shoulder",
                "Practice stress management to reduce muscle tension",
                "Use hands-free devices to avoid cradling phone"
            ],
            "treatment": [
                "Apply ice for acute injury, heat for muscle tension",
                "Over-the-counter pain relievers: ibuprofen, acetaminophen",
                "Gentle neck stretches and range of motion exercises",
                "Maintain normal activities as much as possible",
                "Physical therapy for persistent pain",
                "Massage therapy to reduce muscle tension",
                "Neck collar for short-term support if recommended",
                "Prescription medications for severe pain",
                "Injection therapy for nerve-related pain"
            ]
        },
        
        "Stress Management for Pain Relief": {
            "introduction": """
            Stress and pain have a complex, interconnected relationship. Chronic stress can 
            increase pain sensitivity and contribute to the development of various pain conditions, 
            while chronic pain can create additional stress, creating a difficult cycle. 
            Understanding effective stress management techniques is essential for comprehensive 
            pain management and overall health and well-being.
            """,
            "causes": [
                "Work-related pressures and deadlines",
                "Financial concerns and economic uncertainty",
                "Relationship difficulties and family conflicts",
                "Health problems and chronic pain conditions",
                "Major life changes or traumatic events",
                "Lack of social support and isolation",
                "Poor work-life balance",
                "Information overload and constant connectivity",
                "Perfectionism and unrealistic expectations"
            ],
            "symptoms": [
                "Increased muscle tension and physical pain",
                "Headaches and jaw clenching",
                "Sleep disturbances and insomnia",
                "Digestive issues and appetite changes",
                "Irritability and mood swings",
                "Difficulty concentrating and memory problems",
                "Fatigue and low energy levels",
                "Increased sensitivity to pain",
                "Anxiety and feelings of overwhelm"
            ],
            "prevention": [
                "Develop healthy coping strategies for daily stressors",
                "Maintain regular exercise routine to reduce stress hormones",
                "Practice time management and set realistic goals",
                "Build and maintain strong social support networks",
                "Learn to say no to excessive commitments",
                "Create boundaries between work and personal time",
                "Engage in hobbies and activities you enjoy",
                "Practice mindfulness and present-moment awareness",
                "Maintain healthy lifestyle habits: sleep, nutrition, exercise"
            ],
            "treatment": [
                "Deep breathing exercises and progressive muscle relaxation",
                "Mindfulness meditation and mindfulness-based stress reduction",
                "Regular physical exercise appropriate for pain condition",
                "Cognitive-behavioral therapy to change thought patterns",
                "Yoga and tai chi for mind-body connection",
                "Adequate sleep hygiene and stress-reducing bedtime routine",
                "Professional counseling or therapy for severe stress",
                "Biofeedback training to control physiological responses",
                "Support groups for people with chronic pain conditions"
            ]
        }
    }
    
    # Create output directory
    output_dir = "health_pdfs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create PDFs for each topic
    for topic in topics:
        create_health_pdf(topic, health_content[topic], output_dir)
    
    print(f"Successfully created {len(topics)} health PDF documents in '{output_dir}' directory")

def create_health_pdf(title, content, output_dir):
    """Create a comprehensive PDF for a specific health topic"""
    
    # Sanitize filename
    filename = title.replace(":", "").replace(",", "").replace(" ", "_") + ".pdf"
    filepath = os.path.join(output_dir, filename)
    
    # Create document
    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor='darkblue'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor='darkred'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=10
    )
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 20))
    
    # Add introduction
    story.append(Paragraph("Introduction", heading_style))
    story.append(Paragraph(content['introduction'].strip(), body_style))
    story.append(Spacer(1, 15))
    
    # Add causes section
    story.append(Paragraph("Common Causes", heading_style))
    story.append(Paragraph(
        "Understanding the root causes of this condition is essential for effective prevention and treatment:",
        body_style
    ))
    
    for cause in content['causes']:
        story.append(Paragraph(f"• {cause}", bullet_style))
    
    story.append(Spacer(1, 15))
    
    # Add symptoms section
    story.append(Paragraph("Signs and Symptoms", heading_style))
    story.append(Paragraph(
        "Recognizing these symptoms can help you identify the condition and seek appropriate treatment:",
        body_style
    ))
    
    for symptom in content['symptoms']:
        story.append(Paragraph(f"• {symptom}", bullet_style))
    
    story.append(Spacer(1, 15))
    
    # Add prevention section
    story.append(Paragraph("Prevention Strategies", heading_style))
    story.append(Paragraph(
        "These preventive measures can help reduce the likelihood of developing or worsening this condition:",
        body_style
    ))
    
    for prevention in content['prevention']:
        story.append(Paragraph(f"• {prevention}", bullet_style))
    
    story.append(Spacer(1, 15))
    
    # Add treatment section
    story.append(Paragraph("Treatment Options", heading_style))
    story.append(Paragraph(
        "Various treatment approaches are available, ranging from self-care measures to professional medical intervention:",
        body_style
    ))
    
    for treatment in content['treatment']:
        story.append(Paragraph(f"• {treatment}", bullet_style))
    
    story.append(Spacer(1, 20))
    
    # Add disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        textColor='gray',
        alignment=TA_CENTER
    )
    
    story.append(Paragraph(
        "<b>Medical Disclaimer:</b> This information is for educational purposes only and should not replace "
        "professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare "
        "providers before making any health-related decisions or starting new treatments.",
        disclaimer_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"Created: {filename}")

if __name__ == "__main__":
    # First, let's install the required package
    import subprocess
    import sys
    
    try:
        import reportlab
    except ImportError:
        print("Installing reportlab package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
        import reportlab
    
    # Create the health PDFs
    create_health_pdfs()
