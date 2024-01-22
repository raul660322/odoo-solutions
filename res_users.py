from odoo import models, fields, api, SUPERUSER_ID
import json
from lxml import etree
import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    #Force application of newly created access rules for users created before rules
    #Otherwise, server should be restarted in order to rules to apply immediatly
    def create(self, vals):
        self.clear_caches() 
        res = super(ResUsers, self).create(vals)
        return res

    
    #Force update of user inherited groups
    #When a user in added to a group, it may be added automatically to other groups that are associated to that group.
    #But, if later the group is unassigned, the user remains belonging to those associate (inherited) groups.
    #This code searchs for all inherited groups (inside certain category "categ") and recursively updates the user's membership accordingly.
    def write(self, vals):
        self.clear_caches()
        #Grupos existentes
        categ = self.env.ref('administrator.module_category_administrator').id
        old_groups = self.groups_id.filtered(lambda gr: gr.category_id.id == categ).ids
        res = super(ResUsers, self).write(vals)
        
        #Actualizar los grupos heredados si se quitan grupos
        removed_group_boxes =  {key: value for (key, value) in vals.items() if ("in_group" in key) and not value}
        if removed_group_boxes:
            gr_remove = []
            gr_add =[]
            rem_groups = []
            for k in removed_group_boxes.keys():
                grupo_id = int(k[9:])
                rem_groups.append(grupo_id)
                self.remove_implied_groups(grupo_id, gr_remove)
            quedan_groups = list(set(old_groups)-set(rem_groups))    

            for k in quedan_groups:
                self.add_implied_groups(k, gr_add)

            self.write({
                'groups_id':gr_remove + gr_add
            })
        return res
    
    #Elimina recursivamente los grupos heredados
    def remove_implied_groups(self, grupo_id, gr_remove):
        grupos_implicados = self.env['res.groups'].browse(grupo_id).implied_ids.ids
        for gr in grupos_implicados:
            #No eliminar recursivamente del grupo usuario interno y otros permanentes
            if gr not in [self.env.ref('base.group_user').id, 
                          self.env.ref('hr_timesheet.group_hr_timesheet_user').id,
                          self.env.ref('helpdesk.group_use_sla').id]:
                gr_remove.append((3,gr))
                self.remove_implied_groups(gr, gr_remove)

    #Agrega recursivamente los grupos heredados
    def add_implied_groups(self, grupo_id, gr_add):
        grupos_implicados = self.env['res.groups'].browse(grupo_id).implied_ids.ids
        for gr in grupos_implicados:
            gr_add.append((4,gr))
            self.add_implied_groups(gr, gr_add)

    #This code is used to grant or deny access to certain parts and actions on the form,
    #according to the user membership to a group(hr.group_hr_user)  
    #The method fields_view_get is used to get view data, which are directly modified
    #using xpath method.       
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # When the front-end loads the views it gets the list of available fields
        # for the user (according to its access rights). Later, when the front-end wants to
        # populate the view with data, it only asks to read those available fields.
        # However, in this case, we want the user to be able to read/write its own data,
        # even if they are protected by groups.
        # We make the front-end aware of those fields by sending all field definitions.
        # Note: limit the `sudo` to the only action of "editing own profile" action in order to
        # avoid breaking `groups` mecanism on res.users form view.
        profile_view = self.env.ref("hr.res_users_view_form_profile")
        simple_view = self.env.ref("base.view_users_simple_form")
        original_user = self.env.user
        # if profile_view and view_id == profile_view.id:
        #     self = self.with_user(SUPERUSER_ID)
        result = super(ResUsers, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    
        # Due to using the SUPERUSER the result will contain action that the user may not have access too
        # here we filter out actions that requires special implicit rights to avoid having unusable actions
        # in the dropdown menu.
        # if toolbar and self.env.user != original_user:
        #     self = self.with_user(original_user.id)
        #     if not self.user_has_groups("base.group_erp_manager"):
        #         change_password_action = self.env.ref("base.change_password_wizard_action")
        #         result['toolbar']['action'] = [act for act in result['toolbar']['action'] if act['id'] != change_password_action.id]

        if profile_view and view_id == profile_view.id and not original_user.has_group('hr.group_hr_user'):
            doc = etree.XML(result['arch'])
            for node in doc.xpath("//page[@name='personal_information']"):
                node.set('invisible', '1')
                node.set('modifiers','{"invisible": true}')
            for node in doc.xpath("//page[@name='hr_settings']"):
                node.set('invisible', '1')
                node.set('modifiers','{"invisible": true}')
            for node in doc.xpath("/descendant::group[position()=14]"):
                node.set('invisible', '1')
                node.set('modifiers','{"invisible": true}')
            for node in doc.xpath("//field[@name='email']"):
                node.set('readonly', '1')
                node.set('modifiers','{"readonly": true}')
            result['arch'] = etree.tostring(doc)

        if profile_view and view_id == profile_view.id:
            doc = etree.XML(result['arch'])
            for node in doc.xpath("//field[@name='work_email']"):
                node.set('readonly', '1')
                node.set('modifiers','{"readonly": true}')
            result['arch'] = etree.tostring(doc)

        if simple_view and view_id != profile_view.id and view_type == 'form' and not original_user.has_group('hr.group_hr_user'):
            doc = etree.XML(result['arch'])
            for node in doc.xpath("//form"):
                node.set('create', '0')
                node.set('modifiers','{"create": 0}')
                node.set('edit', '0')
                node.set('modifiers','{"edit": 0}')

            for node in doc.xpath("//field[@name='phone'] | //field[@name='mobile'] | //field[@name='name'] | //field[@name='login']"):
                node.set('readonly', '1')
                node.set('modifiers','{"readonly": true}')

            result['arch'] = etree.tostring(doc)

        
        return result

    def update_profile(self, params, user_profile):
        user = self.sudo().search([
            ("login", "=", params.get('email'))
        ], limit=1)
        profile = user_profile['value'][3]['displayName']
        if profile:
            odoo_profile = self.env['res.groups'].search([('type_user_azure_ad', '=', profile)])
            if odoo_profile:
                if odoo_profile.id not in user.groups_id.ids:
                    _logger.info('ACTUALIZANDO')
                    user.sudo().write({
                        'groups_id': [(6, 0, [odoo_profile.id])],
                        'group_access': profile
                    })