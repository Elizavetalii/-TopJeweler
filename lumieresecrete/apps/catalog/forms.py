from django import forms

from apps.catalog.models import ProductReview
from apps.product_variants.models import ProductVariant


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ('rating', 'comment', 'variant')
        widgets = {
            'rating': forms.Select(attrs={'class': 'select-field'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Поделитесь впечатлениями', 'class': 'text-field'}),
            'variant': forms.Select(attrs={'class': 'select-field'}),
        }
        labels = {
            'rating': 'Оценка',
            'comment': 'Комментарий',
            'variant': 'Вариант (опционально)',
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product is not None:
            self.fields['variant'].queryset = ProductVariant.objects.filter(product=product)
        else:
            self.fields['variant'].queryset = ProductVariant.objects.none()
        self.fields['variant'].required = False
