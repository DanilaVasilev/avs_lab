import torch
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v2
from PIL import Image
import numpy as np

_model_cache = None


def load_model():
    """
    Загружает MobileNetV2 для генерации эмбедингов.

    Returns:
        torch.nn.Module: модель для генерации признаков (выходной размер 1280)
    """
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    model = mobilenet_v2(pretrained=True)
    
    class _EmbedModel(torch.nn.Module):
        def __init__(self, base):
            super().__init__()
            self.features = base.features
            self.pool = torch.nn.AdaptiveAvgPool2d(1)

        def forward(self, x):
            x = self.features(x)
            x = self.pool(x)
            x = x.view(x.size(0), -1)
            return x

    embed_model = _EmbedModel(model)
    embed_model.eval()
    embed_model.to("cpu")

    _model_cache = embed_model
    return _model_cache


def embed_image(image_path) -> np.ndarray:
    """
    Преобразует изображение в эмбединг.

    Args:
        image_path: путь к файлу или PIL.Image

    Returns:
        np.ndarray: вектор размером (1280,)
    """
    if isinstance(image_path, str):
        img = Image.open(image_path).convert("RGB")
    else:
        img = image_path.convert("RGB")

    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                              std=[0.229, 0.224, 0.225])
    ])

    img_tensor = transform(img).unsqueeze(0).to("cpu")

    model = load_model()
    with torch.no_grad():
        emb = model(img_tensor)

    emb = emb.squeeze(0).cpu().numpy()
    return emb.astype(np.float32)
