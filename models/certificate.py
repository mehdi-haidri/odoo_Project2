from odoo import models, fields, api


class CertificateExtension(models.Model):
    _name = 'elearning.certificate'
    _description = 'Certificate'
    
    # Basic fields
    enrollment_id = fields.Many2one('elearning.enrollment', string='Enrollment', required=True, ondelete='cascade')
    name = fields.Char(string='Certificate Name', compute='_compute_name', store=True)
    student_id = fields.Many2one('res.partner', string='Student', related='enrollment_id.student_id', readonly=True)
    course_id = fields.Many2one('elearning.course', string='Course', related='enrollment_id.course_id', readonly=True)
    grade = fields.Float(string='Grade')
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today)
    expiration_date = fields.Date(string='Expiration Date')
    is_valid = fields.Boolean(string='Is Valid', compute='_compute_is_valid', store=True)
    
    # Additional fields for enhanced certificate management
    certificate_code = fields.Char(string='Certificate Code', unique=True)
    certificate_hash = fields.Char(string='Certificate Hash')
    digital_badge = fields.Image(string='Digital Badge')
    certificate_file = fields.Binary(string='Certificate PDF')
    can_share = fields.Boolean(string='Can Share', default=True)
    shared_count = fields.Integer(string='Times Shared', default=0)
    
    @api.depends('enrollment_id.student_id', 'enrollment_id.course_id')
    def _compute_name(self):
        for cert in self:
            if cert.enrollment_id and cert.enrollment_id.student_id and cert.enrollment_id.course_id:
                cert.name = f"{cert.enrollment_id.student_id.name} - {cert.enrollment_id.course_id.name}"
            else:
                cert.name = "Certificate"
    
    @api.depends('expiration_date')
    def _compute_is_valid(self):
        today = fields.Date.today()
        for cert in self:
            cert.is_valid = not cert.expiration_date or cert.expiration_date >= today
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate certificate code on creation"""
        for vals in vals_list:
            if not vals.get('certificate_code'):
                import uuid
                vals['certificate_code'] = str(uuid.uuid4())[:12].upper()
            if not vals.get('certificate_hash'):
                import hashlib
                vals['certificate_hash'] = hashlib.sha256(str(vals).encode()).hexdigest()
        
        return super().create(vals_list)
