from odoo import http
from odoo.http import request


class ELearningController(http.Controller):

    @http.route('/elearning/', type='http', auth='public', website=True)
    def courses_list(self, **kw):
        """Display list of available courses"""
        search = kw.get('search')
        min_price = kw.get('min_price')
        max_price = kw.get('max_price')
        
        domain = [('is_published', '=', True)]
        
        if search:
            search = search.strip()
            if search:
                domain.append(('name', 'ilike', search))
            
        if min_price:
            try:
                domain.append(('price', '>=', float(min_price)))
            except ValueError:
                pass
                
        if max_price:
            try:
                domain.append(('price', '<=', float(max_price)))
            except ValueError:
                pass

        courses = request.env['elearning.course'].sudo().search(domain)
        
        enrolled_course_ids = []
        if not request.env.user._is_public():
            enrolled_course_ids = request.env['elearning.enrollment'].search([
                ('student_id', '=', request.env.user.partner_id.id)
            ]).mapped('course_id.id')
            
        return request.render('odoo_Project2.courses_template', {
            'courses': courses,
            'enrolled_course_ids': enrolled_course_ids,
            'search_term': search,
            'min_price': min_price,
            'max_price': max_price,
        })

    @http.route('/elearning/my_courses', type='http', auth='user', website=True)
    def my_courses(self, **kw):
        """Display list of enrolled courses"""
        search = kw.get('search')
        min_price = kw.get('min_price')
        max_price = kw.get('max_price')

        enrollments = request.env['elearning.enrollment'].search([
            ('student_id', '=', request.env.user.partner_id.id)
        ])
        courses = enrollments.mapped('course_id').sudo()
        
        # Filter in python since we have a recordset of courses from enrollments
        if search:
            search = search.strip()
            if search:
                courses = courses.filtered(lambda c: search.lower() in c.name.lower())
            
        if min_price:
            try:
                courses = courses.filtered(lambda c: c.price >= float(min_price))
            except ValueError:
                pass
                
        if max_price:
            try:
                courses = courses.filtered(lambda c: c.price <= float(max_price))
            except ValueError:
                pass
        
        return request.render('odoo_Project2.courses_template', {
            'courses': courses,
            'enrolled_course_ids': courses.ids,
            'my_courses_mode': True,
            'search_term': search,
            'min_price': min_price,
            'max_price': max_price,
        })

    @http.route('/elearning/my_certificates', type='http', auth='public', website=True)
    def my_certificates(self, **kw):
        """Display list of obtained certificates"""
        if request.env.user._is_public():
            return request.redirect('/web/login?redirect=/elearning/my_certificates')
            
        certificates = request.env['elearning.certificate'].sudo().search([
            ('student_id', '=', request.env.user.partner_id.id)
        ])
        
        return request.render('odoo_Project2.my_certificates_template', {
            'certificates': certificates,
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
        
        # Get reviews
        reviews = request.env['elearning.course.review'].search([('course_id', '=', course_id)])
        user_review = False
        if not request.env.user._is_public():
            user_review = request.env['elearning.course.review'].search([
                ('course_id', '=', course_id),
                ('user_id', '=', request.env.user.id)
            ], limit=1)

        return request.render('odoo_Project2.course_detail_template', {
            'course': course,
            'enrollment': enrollment,
            'reviews': reviews,
            'user_review': user_review,
        })

    @http.route('/elearning/course/review/submit', type='http', auth='user', methods=['POST'], website=True)
    def submit_review(self, **kw):
        course_id = int(kw.get('course_id'))
        rating = kw.get('rating')
        comment = kw.get('comment')
        
        # Check enrollment
        enrollment = request.env['elearning.enrollment'].search([
            ('course_id', '=', course_id),
            ('student_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        if not enrollment:
             return request.redirect(f'/elearning/course/{course_id}')

        # Check existing review
        existing_review = request.env['elearning.course.review'].search([
            ('course_id', '=', course_id),
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        if not existing_review:
            request.env['elearning.course.review'].create({
                'course_id': course_id,
                'user_id': request.env.user.id,
                'rating': rating,
                'comment': comment,
            })
            
        return request.redirect(f'/elearning/course/{course_id}')

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

    @http.route('/elearning/lesson/<int:lesson_id>', type='http', auth='public', website=True)
    def lesson_view(self, lesson_id, **kw):
        """Display lesson content"""
        lesson = request.env['elearning.lesson'].sudo().browse(lesson_id)
        
        if not lesson.exists() or not lesson.is_published:
            if lesson.exists():
                return request.redirect(f'/elearning/course/{lesson.course_id.id}')
            return request.render('website.404')

        # Check enrollment
        enrollment = False
        if not request.env.user._is_public():
            enrollment = request.env['elearning.enrollment'].search([
                ('course_id', '=', lesson.course_id.id),
                ('student_id', '=', request.env.user.partner_id.id)
            ], limit=1)
        
        # Access check: Must be enrolled OR lesson must be a preview
        if not enrollment and not lesson.is_preview:
            return request.redirect(f'/elearning/course/{lesson.course_id.id}')
        
        # Get existing submission if any (only for logged in users)
        submission = False
        if not request.env.user._is_public():
            submission = request.env['elearning.submission'].search([
                ('lesson_id', '=', lesson_id),
                ('student_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        return request.render('odoo_Project2.lesson_template', {
            'lesson': lesson,
            'enrollment': enrollment,
            'submission': submission,
        })

    @http.route('/elearning/lesson/<int:lesson_id>/assignment/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def submit_assignment(self, lesson_id, **kw):
        """Handle assignment submission"""
        lesson = request.env['elearning.lesson'].browse(lesson_id)
        enrollment = request.env['elearning.enrollment'].search([
            ('course_id', '=', lesson.course_id.id),
            ('student_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        if not enrollment:
            return request.redirect(f'/elearning/course/{lesson.course_id.id}')
            
        file = kw.get('submission_file')
        notes = kw.get('submission_text')
        
        if file:
            import base64
            file_content = base64.b64encode(file.read())
            
            # Check for existing submission
            submission = request.env['elearning.submission'].search([
                ('lesson_id', '=', lesson_id),
                ('student_id', '=', request.env.user.partner_id.id)
            ], limit=1)
            
            vals = {
                'lesson_id': lesson_id,
                'student_id': request.env.user.partner_id.id,
                'submission_file': file_content,
                'submission_filename': file.filename,
                'submission_text': notes,
                'state': 'submitted',
            }
            
            if submission:
                submission.write(vals)
            else:
                request.env['elearning.submission'].create(vals)
                
        return request.redirect(f'/elearning/lesson/{lesson_id}')

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

    @http.route('/elearning/certificate/download/<int:enrollment_id>', type='http', auth='public', website=True)
    def download_certificate(self, enrollment_id, **kw):
        """Download certificate PDF"""
        if request.env.user._is_public():
            return request.redirect('/web/login')
            
        enrollment = request.env['elearning.enrollment'].browse(enrollment_id)
        
        # Check authorization
        if enrollment.student_id.id != request.env.user.partner_id.id:
            return request.redirect('/elearning/')
            
        # Find certificate
        certificate = request.env['elearning.certificate'].sudo().search([
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

    @http.route('/elearning/certificate/<int:certificate_id>', type='http', auth='public', website=True)
    def view_certificate(self, certificate_id, **kw):
        """Display certificate"""
        if request.env.user._is_public():
            return request.redirect('/web/login')
            
        certificate = request.env['elearning.certificate'].sudo().browse(certificate_id)
        
        # Check authorization
        if certificate.student_id.id != request.env.user.partner_id.id and not request.env.user.has_group('base.group_system'):
            return request.render('website.404')
        
        return request.render('odoo_Project2.certificate_template', {
            'certificate': certificate,
        })
