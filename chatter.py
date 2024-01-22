from multiprocessing.connection import wait
from odoo import api, fields, models, tools, _

class InheritModel(models.Model):
    _name = 'model_inherited'
    _inherit = ['model_inherited', 'mail.thread', 'mail.activity.mixin']
    name = fields.Char(tracking=True)
    stage_ids = fields.Many2many("model.stage",tracking=True)
    tag_ids = fields.Many2many("model.tag", tracking=True)

    #Implements chatter features for many2many fields
    def write(self, vals):
        body = ''
        for rec in self:
            if 'tag_ids' in vals:
                new_values = vals['tag_ids'][0][2]
                old_values = self.tag_ids.ids
                added = list(set(new_values) - set(old_values))
                removed = list(set(old_values) - set(new_values))
                listaAdd = ''
                listaRem = ''

                for el in added:
                    listaAdd += \
                        f'<li>' \
                        f'<div role="group" class="o_Message_trackingValue">' \
                        f'<div class="o_Message_trackingValueFieldName o_Message_trackingValueItem">{rec.env["model.tag"].browse(el).name}</div>' \
                        f'</div>' \
                        f'</li>'
                for el in removed:
                    listaRem += \
                        f'<li>' \
                        f'<div role="group" class="o_Message_trackingValue">' \
                        f'<div class="o_Message_trackingValueFieldName o_Message_trackingValueItem">{rec.env["model.tag"].browse(el).name}</div>' \
                        f'</div>' \
                        f'</li>'
                body = '<h6>Modificación en Categorías:</h6>'
                if added or removed:
                    if added:
                        body += f'<h6>Agregado:</h6><ul class="o_Message_trackingValues">{listaAdd}</ul>'
                    if removed:
                        body += f'<h6>Eliminado:</h6><ul class="o_Message_trackingValues">{listaRem}</ul>'

            if 'stage_ids' in vals:
                new_values = vals['stage_ids'][0][2]
                old_values = self.stage_ids.ids
                added = list(set(new_values) - set(old_values))
                removed = list(set(old_values) - set(new_values))
                listaAdd = ''
                listaRem = ''

                for el in added:
                    listaAdd += \
                        f'<li>' \
                        f'<div role="group" class="o_Message_trackingValue">' \
                        f'<div class="o_Message_trackingValueFieldName o_Message_trackingValueItem">{rec.env["model.stage"].browse(el).name}</div>' \
                        f'</div>' \
                        f'</li>'
                for el in removed:
                    listaRem += \
                        f'<li>' \
                        f'<div role="group" class="o_Message_trackingValue">' \
                        f'<div class="o_Message_trackingValueFieldName o_Message_trackingValueItem">{rec.env["model.stage"].browse(el).name}</div>' \
                        f'</div>' \
                        f'</li>'
                body = '<h6>Modificación en Exclude Stages:</h6>'
                if added or removed:
                    if added:
                        body += f'<h6>Agregado:</h6><ul class="o_Message_trackingValues">{listaAdd}</ul>'
                    if removed:
                        body += f'<h6>Eliminado:</h6><ul class="o_Message_trackingValues">{listaRem}</ul>'

            rec.message_post(body=body)
        result = super(InheritModel, self).write(vals)
        return result
