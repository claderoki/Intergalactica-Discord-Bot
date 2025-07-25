import datetime
import typing
from typing import List, Optional, Type, Dict, Set, TypeVar, Generic, Callable

import discord
import peewee
from discord import SelectOption, TextStyle

from src.classes import Labeled
from src.models import Reminder
from src.models.base import LongTextField


class ReminderMenu(discord.ui.View):
    def __init__(self, user_id: int, when: datetime.datetime, message: str):
        super(ReminderMenu, self).__init__()
        self.user_id = user_id
        self.when = when
        self.message = message

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label='Remind me', style=discord.ButtonStyle.red)
    async def remind_me(self, interaction: discord.Interaction, _button: discord.ui.Button):
        Reminder.create(
            user_id=interaction.user.id,
            channel_id=None,
            message=self.message,
            due_date=self.when
        )
        await interaction.response.send_message(content='All right, I\'ll be sure to remind you.')


async def edit_view(interaction: discord.Interaction, model: peewee.Model, view: discord.ui.View = None):
    view = view or guess_view(model)
    if isinstance(view, discord.ui.Modal):
        await interaction.response.send_modal(view)
    else:
        await interaction.response.send_message(view=view)
    await view.wait()


def __get_views(model, items, constr) -> List[discord.ui.View]:
    if len(items) == 0:
        return []
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


def guess_view(model: peewee.Model) -> discord.ui.View:
    return forms_to_view(model, guess(model.__class__))


def forms_to_view(model: peewee.Model, forms: List['FieldForm']) -> discord.ui.View:
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
    views.extend(__get_views(model, others, EditView))
    views.extend(__get_views(model, text_inputs, EditModal))

    for i in range(1, len(views)):
        views[i - 1].after = views[i]
    return views[0]


def guess(model: Type[peewee.Model]) -> List['FieldForm']:
    fields = []
    for attr in vars(model):
        attribute = getattr(model, attr)
        if isinstance(attribute, peewee.Field) and attr != 'id':
            fields.append(attribute)
    return guess_for_fields(fields)


def guess_for_fields(fields: List[peewee.Field]) -> List['FieldForm']:
    forms = {}
    for field in fields:
        if field.name == 'id':
            continue
        if field.name not in forms:
            forms[field.name] = FieldForm(field, not field.null)
    return list(forms.values())


class FieldForm:
    def __init__(self, field: peewee.Field, required: bool = False):
        self.field = field
        self._required = required
        self.item = None

    @classmethod
    def required(cls, field: peewee.Field):
        return cls(field, True)

    def get_item(self) -> Optional[discord.ui.Item]:
        if self.item is None:
            self.item = self.__get_item()
        return self.item

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
            default=str(self.field.default),
            style=TextStyle.long if isinstance(self.field, LongTextField) else TextStyle.short
        )


class EditModal(discord.ui.Modal, title='Edit'):
    def __init__(self, model: peewee.Model):
        super(self.__class__, self).__init__()
        self.model = model
        self.forms: Dict[str, discord.ui.TextInput] = {}
        self.after: Optional[discord.ui.Modal] = None

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


T = TypeVar('T')


class DataSelect(discord.ui.Select, Generic[T]):
    def __init__(self, data: List[T], to_select):
        self.data = {}
        options = []
        for x in data:
            select: discord.SelectOption = to_select(x)
            self.data[select.value] = x
            options.append(select)
        super().__init__(min_values=1, max_values=1, options=options)
        self.selected: List[T] = []

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.selected = [self.data[x] for x in self.values]
        self.view.stop()


def _create_callback_for(component: discord.ui.Item, callback: Callable[[discord.ui.Item, discord.Interaction], typing.Awaitable]):
    def wrapper(interaction: discord.Interaction):
        return callback(component, interaction)
    return wrapper


async def dropdown(interaction: discord.Interaction, labeleds: List[Labeled], selected_keys: List[str] = None):
    selected_keys = selected_keys or []
    view = discord.ui.View()
    values = {x.get_key(): x for x in labeleds}
    select = discord.ui.Select(min_values=0, max_values=len(values))
    for key, label in values.items():
        select.add_option(label=label.get_label(), value=key, default=key in selected_keys)

    async def _callback(component: discord.ui.Select, interaction: discord.Interaction):
        await interaction.response.defer()
        component.view.stop()

    select.callback = _create_callback_for(select, _callback)
    view.add_item(select)
    await interaction.response.send_message(view=view)
    await view.wait()
    return [values[int(x)] for x in select.values]


class DataChoice(discord.ui.View, Generic[T]):
    def __init__(self, data: List[T], to_select: Callable[[T], discord.SelectOption]):
        super(DataChoice, self).__init__()
        self.add_item(DataSelect(data, to_select))

    def get_selected(self) -> List[T]:
        select: DataSelect = self.children[0]
        return select.selected

    def get_first_or_none(self) -> Optional[T]:
        selected = self.get_selected()
        if len(selected) == 0:
            return None
        return selected[0]


class BooleanChoice(discord.ui.View):
    def __init__(self, default: bool = False):
        super(BooleanChoice, self).__init__()
        self.value = default

    options = [discord.SelectOption(label='Yes'), discord.SelectOption(label='No')]

    @discord.ui.select(placeholder='Choose', min_values=1, max_values=1, options=options)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.value = select.values[0] == 'Yes'
        await interaction.response.defer()
        self.stop()


class JoinMenu(discord.ui.View):
    def __init__(self):
        super(JoinMenu, self).__init__()
        self.user_ids: Set[int] = set()

    def get_content(self) -> str:
        return "\n".join(map(lambda x: f'<@{x}>', self.user_ids))

    @discord.ui.button(label='Join', style=discord.ButtonStyle.red)
    async def join(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.user_ids.add(interaction.user.id)
        await interaction.response.edit_message(content=self.get_content(), view=self)

    @discord.ui.button(label='Leave', style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.user_ids.remove(interaction.user.id)
        await interaction.response.edit_message(content=self.get_content(), view=self)

    @discord.ui.button(label='Start', style=discord.ButtonStyle.red)
    async def start(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.stop()
        await interaction.response.defer()


async def wait_for_players(interaction: discord.Interaction) -> Set[int]:
    menu = JoinMenu()
    menu.user_ids.add(interaction.user.id)
    await interaction.response.send_message(menu.get_content(), view=menu)
    await menu.wait()
    return menu.user_ids
