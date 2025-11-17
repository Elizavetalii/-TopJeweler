from django import forms


class BackupForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        initial=True,
        label="Подтверждаю создание резервной копии",
    )


class RestoreForm(forms.Form):
    backup_file = forms.FileField(label="Файл резервной копии (.json)")
