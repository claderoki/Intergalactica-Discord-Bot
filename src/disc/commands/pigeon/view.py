from typing import List, Optional, Type, Dict

import discord
import peewee
from discord import SelectOption


async def edit_view(interaction: discord.Interaction, model: peewee.Model):
    view = guess_view(model)
    if isinstance(view, discord.ui.Modal):
        await interaction.response.send_modal(view)
    else:
        await interaction.response.send_message(view=view)
    await view.wait()


def __get_views(model, items, constr) -> List[discord.ui.View]:
    views: List[discord.ui.View] = [constr(model)]
    for i in range(len(items)):
        item = items[i]
        try:
            views[-1].add_form(item)
        except ValueError:
            view = constr(model)
            view.add_form(item)
            views.append(view)
    return views


def guess_view(model: peewee.Model, forms: List['FieldForm'] = None) -> discord.ui.View:
    forms = forms or guess(model.__class__)
    text_inputs = []
    others = []

    for x in forms:
        if isinstance(x.get_item(), discord.ui.TextInput):
            text_inputs.append(x)
        else:
            if isinstance(x, discord.ui.Select) and not x.options:
                continue
            others.append(x)

    views = []
    if others:
        views.extend(__get_views(model, others, EditView))
    if text_inputs:
        views.extend(__get_views(model, text_inputs, EditModal))

    for i in range(1, len(views)):
        views[i-1].after = views[i]
    print(views)
    return views[0]

    # base = None
    # base_modal = None
    # if text_inputs:
    #     base_modal = EditModal(model)
    #     base = base_modal
    #     modal = base_modal
    #     for i in range(len(text_inputs)):
    #         input = text_inputs[i]
    #         try:
    #             modal.add_form(input)
    #         except ValueError:
    #             new = EditModal(model)
    #             new.add_form(input)
    #             modal.after = new
    #             modal = new
    # if others:
    #     base_view = EditView(model)
    #     base = base_view
    #     last_view = base_view
    #     for i in range(len(others)):
    #         other = others[i]
    #         try:
    #             last_view.add_form(other)
    #         except ValueError:
    #             view = EditView(model)
    #             view.add_form(other)
    #             last_view.after = view
    #             last_view = view
    #     last_view.after = base_modal
    return base


def guess(model: Type[peewee.Model]) -> List['FieldForm']:
    forms = {}
    for attr in vars(model):
        if attr == 'id':
            continue
        attribute = getattr(model, attr)
        if isinstance(attribute, peewee.Field):
            forms[attribute.name] = FieldForm(attribute, not attribute.null)
    return list(forms.values())


class FieldForm:
    def __init__(self, field: peewee.Field, required: bool = False):
        self.field = field
        self._required = required
        self._item = None

    @classmethod
    def required(cls, field: peewee.Field):
        return cls(field, True)

    def get_item(self) -> Optional[discord.ui.Item]:
        if self._item is None:
            self._item = self.__get_item()
        return self._item

    def __get_select_options(self) -> List[SelectOption]:
        if isinstance(self.field, peewee.ForeignKeyField):
            # todo, what if no name...
            return [SelectOption(label=x.name, value=x.id) for x in self.field.rel_model]
        if isinstance(self.field, peewee.BooleanField):
            return [SelectOption(label=x, value=str(i)) for i, x in enumerate(['No', 'Yes'])]

    def __get_item(self) -> Optional[discord.ui.Item]:
        select_options = self.__get_select_options()
        if select_options is not None:
            return discord.ui.Select(
                placeholder=str(self.field.name),
                options=select_options)

        return discord.ui.TextInput(
            label=str(self.field.name),
            required=self._required,
            default=str(self.field.default)
        )


class EditModal(discord.ui.Modal, title='Edit'):
    def __init__(self, model: peewee.Model):
        super(self.__class__, self).__init__()
        self.model = model
        self.forms: Dict[str, discord.ui.TextInput] = {}
        self.after: discord.ui.Modal = None

    def add_form(self, form: FieldForm):
        item = form.get_item()
        if item is None:
            return
        self.add_item(item)
        self.forms[form.field.name] = item

    def set_defaults(self):
        for name, item in self.forms.items():
            value = getattr(self.model, name)
            item.default = value

    async def pre_save(self):
        pass

    async def post_save(self):
        pass

    async def on_submit(self, interaction: discord.Interaction):
        for name, item in self.forms.items():
            setattr(self.model, name, item.value)
        await self.pre_save()
        await self.post_save()
        if self.after:
            print([x for x in self.after.__modal_children_items__])
            await interaction.response.send_modal(self.after)
            await self.after.wait()
        else:
            await interaction.response.defer()


class EditView(discord.ui.View):
    def __init__(self, model: peewee.Model):
        super(self.__class__, self).__init__()
        self.model = model
        self.after = None
        self.forms: Dict[str, discord.ui.TextInput] = {}

    def add_form(self, form: FieldForm):
        item = form.get_item()
        if item is None or isinstance(item, discord.ui.Select) and not item.options:
            return
        name = form.field.name
        if isinstance(item, discord.ui.Select):
            item.callback = self.__select_callback(name, item)

        self.add_item(item)
        self.forms[name] = item

    async def pre_save(self):
        pass

    async def post_save(self):
        pass

    def __select_callback(self, name: str, select: discord.ui.Select):
        async def callback(interaction: discord.Interaction):
            value = select.values[0] if select.values else None
            if select.options == ['Yes', 'No']:
                value = value == '1'
            setattr(self.model, name, value)
            await interaction.response.defer()
        return callback

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.red)
    async def save(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.pre_save()
        await self.post_save()
        if self.after:
            if isinstance(self.after, discord.ui.Modal):
                await interaction.response.send_modal(self.after)
            else:
                await interaction.response.send_message(view=self.after)
            await self.after.wait()
        else:
            await interaction.response.defer()
        self.stop()
