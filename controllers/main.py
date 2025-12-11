from odoo import http
from odoo.http import request


class ELearningController(http.Controller):

    @http.route('/elearning/', type='http', auth='public', website=True)
    def courses_list(self, **kw):
        """Display list of available courses"""
        courses = request.env['elearning.course'].sudo().search([('is_published', '=', True)])
        return request.render('odoo_Project2.courses_template', {
            'courses': courses,
        })

    @http.route('/elearning/course/<int:course_id>', type='http', auth='public', website=True)
    def course_detail(self, course_id, **kw):
        """Display course details and lessons"""
        course = request.env['elearning.course'].sudo().browse(course_id)
        
        if not course.exists() or not course.is_published:
            return request.render('website.404')

        enrollment = False
        if not request.env.user._is_public():
            enrollment = request.env['elearning.enrollment'].search([
                ('course_id', '=', course_id),
                ('student_id', '=', request.env.user.partner_id.id)
            ], limit=1)
        
        return request.render('odoo_Project2.course_detail_template', {
            'course': course,
            'enrollment': enrollment,
        })

    @http.route('/elearning/enroll/<int:course_id>', type='http', auth='user', methods=['POST'], website=True)
    def enroll_course(self, course_id, **kw):
        """Enroll user in a course"""
        course = request.env['elearning.course'].browse(course_id)
        student = request.env.user.partner_id
        
        # Check if already enrolled
        existing = request.env['elearning.enrollment'].search([
            ('course_id', '=', course_id),
            ('student_id', '=', student.id)
        ])
        
        if not existing:
            request.env['elearning.enrollment'].create({
                'course_id': course_id,
                'student_id': student.id,
                'status': 'active',
            })
        
        return request.redirect(f'/elearning/course/{course_id}')

    @http.route('/elearning/lesson/<int:lesson_id>', type='http', auth='user', website=True)
    def lesson_view(self, lesson_id, **kw):
        """Display lesson content"""
        lesson = request.env['elearning.lesson'].browse(lesson_id)
        
        if not lesson.exists() or not lesson.is_published:
            return request.redirect(f'/elearning/course/{lesson.course_id.id}')

        enrollment = request.env['elearning.enrollment'].search([
            ('course_id', '=', lesson.course_id.id),
            ('student_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        if not enrollment:
            return request.redirect(f'/elearning/course/{lesson.course_id.id}')
        
        return request.render('odoo_Project2.lesson_template', {
            'lesson': lesson,
            'enrollment': enrollment,
        })

    @http.route('/elearning/lesson/<int:lesson_id>/complete', type='http', auth='user', methods=['POST'], website=True)
    def complete_lesson(self, lesson_id, **kw):
        """Mark a lesson as completed"""
        lesson = request.env['elearning.lesson'].browse(lesson_id)
        enrollment = request.env['elearning.enrollment'].search([
            ('course_id', '=', lesson.course_id.id),
            ('student_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        if enrollment:
            enrollment.mark_lesson_complete(lesson_id)
        
        return request.redirect(f'/elearning/lesson/{lesson_id}')

    @http.route('/elearning/lesson/<int:lesson_id>/quiz/submit', type='http', auth='user', methods=['POST'], website=True)
    def submit_quiz(self, lesson_id, **kw):
        """Handle quiz submission"""
        lesson = request.env['elearning.lesson'].browse(lesson_id)
        enrollment = request.env['elearning.enrollment'].search([
            ('course_id', '=', lesson.course_id.id),
            ('student_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        if not enrollment:
            return request.redirect(f'/elearning/course/{lesson.course_id.id}')

        # Calculate score
        total_questions = len(lesson.question_ids)
        correct_answers = 0
        user_answers = {}
        
        for question in lesson.question_ids:
            answer_key = f'question_{question.id}'
            user_answer = kw.get(answer_key)
            user_answers[str(question.id)] = user_answer
            
            if question.question_type == 'multiple_choice':
                # Check if selected option is correct
                if user_answer:
                    selected_option = request.env['elearning.lesson.question.option'].browse(int(user_answer))
                    if selected_option.exists() and selected_option.is_correct:
                        correct_answers += 1
            elif question.question_type == 'text':
                # Case insensitive comparison
                if user_answer and user_answer.strip().lower() == question.correct_answer_text.strip().lower():
                    correct_answers += 1
        
        score = 0
        if total_questions > 0:
            score = (correct_answers / total_questions) * 100
            
        passed = score >= lesson.quiz_passing_score
        
        if passed:
            enrollment.mark_lesson_complete(lesson_id)
            
        quiz_results = {
            'score': int(score),
            'passed': passed,
            'user_answers': user_answers,
            'total_questions': total_questions,
            'correct_count': correct_answers
        }
        
        return request.render('odoo_Project2.lesson_template', {
            'lesson': lesson,
            'enrollment': enrollment,
            'quiz_results': quiz_results
        })

    @http.route('/elearning/certificate/download/<int:enrollment_id>', type='http', auth='user', website=True)
    def download_certificate(self, enrollment_id, **kw):
        """Download certificate PDF"""
        enrollment = request.env['elearning.enrollment'].browse(enrollment_id)
        
        # Check authorization
        if enrollment.student_id.id != request.env.user.partner_id.id:
            return request.redirect('/elearning/')
            
        # Find certificate
        certificate = request.env['elearning.certificate'].search([
            ('enrollment_id', '=', enrollment.id)
        ], limit=1)
        
        if not certificate:
            return request.redirect(f'/elearning/course/{enrollment.course_id.id}')
            
        # Generate PDF
        report = request.env.ref('odoo_Project2.action_report_elearning_certificate')
        pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(report, [certificate.id])
        
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="Certificate - {enrollment.course_id.name}.pdf"'),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route('/elearning/certificate/<int:certificate_id>', type='http', auth='user', website=True)
    def view_certificate(self, certificate_id, **kw):
        """Display certificate"""
        certificate = request.env['elearning.certificate'].browse(certificate_id)
        
        # Check authorization
        if certificate.student_id.id != request.env.user.partner_id.id and not request.env.user.has_group('base.group_system'):
            return request.render('website.404')
        
        return request.render('odoo_Project2.certificate_template', {
            'certificate': certificate,
        })

    @http.route('/elearning/my-certificates', type='http', auth='user', website=True)
    def my_certificates(self, **kw):
        """Display user's certificates"""
        user_partner = request.env.user.partner_id
        certificates = request.env['elearning.certificate'].search([
            ('student_id', '=', user_partner.id)
        ])
        
        return request.render('odoo_Project2.my_certificates_template', {
            'certificates': certificates,
        })
