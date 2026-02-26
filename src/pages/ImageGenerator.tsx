import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import Icon from '@/components/ui/icon';

export default function ImageGenerator() {
  const { toast } = useToast();
  const location = useLocation();
  const [task, setTask] = useState('');
  const [style, setStyle] = useState('фотореализм');
  const [aspectRatio, setAspectRatio] = useState('квадрат');
  const [imageModel, setImageModel] = useState<'flash' | 'pro'>('flash');
  const [generatedImageUrl, setGeneratedImageUrl] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (location.state?.initialPrompt) {
      setTask(location.state.initialPrompt);
      toast({
        title: 'Промпт загружен! ✨',
        description: 'Описание изображения создано на основе вашего поста',
      });
    }
  }, [location.state, toast]);

  const styles = [
    { value: 'фотореализм', label: '📷 Фотореализм', prompt: 'Photorealistic, ultra-detailed, professional photography' },
    { value: 'иллюстрация', label: '🎨 Иллюстрация', prompt: 'Digital illustration, artistic style, vibrant colors' },
    { value: 'мультяшный', label: '🎬 Мультяшный стиль', prompt: 'Cartoon style, animated, colorful, fun' },
    { value: 'минимализм', label: '⚪ Минимализм', prompt: 'Minimalist design, clean lines, simple composition' },
    { value: 'акварель', label: '🖌️ Акварель', prompt: 'Watercolor painting style, soft colors, artistic brush strokes' },
    { value: '3d_render', label: '🎯 3D рендер', prompt: '3D render, CGI, modern digital art, clean look' },
    { value: 'аниме', label: '✨ Аниме', prompt: 'Anime style, manga art, Japanese animation aesthetic' },
    { value: 'комикс', label: '💥 Комикс', prompt: 'Comic book style, bold lines, pop art colors' },
    { value: 'винтаж', label: '🕰️ Винтаж', prompt: 'Vintage style, retro aesthetic, nostalgic feel' },
    { value: 'неон', label: '💜 Неон', prompt: 'Neon lights, cyberpunk aesthetic, vibrant glow effects' },
    { value: 'пастель', label: '🌸 Пастель', prompt: 'Pastel colors, soft tones, dreamy atmosphere' },
    { value: 'граффити', label: '🎨 Граффити', prompt: 'Graffiti art style, urban street art, bold spray paint' },
  ];

  const aspectRatios = [
    { value: 'квадрат', label: '◼️ Квадрат 1:1', size: '1080x1080', description: 'Instagram, VK пост' },
    { value: 'горизонтальный', label: '◻️ Горизонтальный 16:9', size: '1920x1080', description: 'YouTube, Telegram' },
    { value: 'вертикальный', label: '▭ Вертикальный 9:16', size: '1080x1920', description: 'Stories, Reels' },
    { value: 'горизонтальный_широкий', label: '▬ Широкий 3:2', size: '1200x628', description: 'Facebook, VK баннер' },
  ];

  const generateImage = async () => {
    if (!task.trim()) {
      toast({
        title: 'Ошибка',
        description: 'Опишите, какое изображение хотите создать',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    setGeneratedImageUrl('');

    try {
      const response = await fetch('https://functions.yandexcloud.net/d4e0l4059mc7lrjj3d3b', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task,
          style,
          aspectRatio,
          imageModel
        }),
      });

      const data = await response.json();
      
      if (response.ok && data.imageUrl) {
        setGeneratedImageUrl(data.imageUrl);
        toast({
          title: 'Готово! 🎉',
          description: 'Изображение успешно создано',
        });
      } else {
        throw new Error(data.error || 'Не удалось создать изображение');
      }
    } catch (error) {
      toast({
        title: 'Ошибка генерации',
        description: 'Не удалось создать изображение. Попробуйте еще раз.',
        variant: 'destructive',
      });
      console.error(error);
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadImage = async () => {
    if (!generatedImageUrl) return;
    
    try {
      const response = await fetch(generatedImageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `anyagpt_image_${Date.now()}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: 'Загружено! 💾',
        description: 'Изображение сохранено на устройство',
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось загрузить изображение',
        variant: 'destructive',
      });
    }
  };

  const selectedStyleData = styles.find(s => s.value === style);
  const selectedAspectData = aspectRatios.find(ar => ar.value === aspectRatio);

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5 p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-secondary to-accent rounded-full shadow-lg">
            <span className="text-3xl">🎨</span>
            <h1 className="text-2xl md:text-3xl font-bold text-white">AnyaGPT Image Generator</h1>
            <span className="text-3xl">🖼️</span>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Создавайте уникальные изображения для соцсетей с помощью Gemini 2.5 Flash Image
          </p>
          <div className="flex gap-4 justify-center">
            <Link to="/">
              <Button variant="outline" size="lg" className="font-semibold">
                📝 Текст постов
              </Button>
            </Link>
            <Button variant="default" size="lg" className="font-semibold">
              🎨 Изображения
            </Button>
            <Link to="/documents">
              <Button variant="outline" size="lg" className="font-semibold">
                📚 Документы
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-5 gap-6">
          <Card className="md:col-span-2 p-6 space-y-6 shadow-xl border-2 hover:border-secondary/50 transition-all duration-300">
            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Wand2" size={20} className="text-secondary" />
                Что создать?
              </Label>
              <Textarea
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="Опишите, какое изображение вы хотите получить..."
                className="min-h-[120px] resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Palette" size={20} className="text-secondary" />
                Стиль изображения
              </Label>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {styles.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              {selectedStyleData && (
                <p className="text-xs text-muted-foreground italic">
                  {selectedStyleData.prompt}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Cpu" size={20} className="text-secondary" />
                Модель
              </Label>
              <select
                value={imageModel}
                onChange={(e) => setImageModel(e.target.value as 'flash' | 'pro')}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="flash">⚡ Быстрая (Flash) — быстрее, экономнее</option>
                <option value="pro">✨ Качество (Pro) — лучше детали, ~12₽/картинка</option>
              </select>
              <p className="text-xs text-muted-foreground">
                {imageModel === 'pro' ? 'Nano Banana Pro: выше качество и детализация.' : 'Gemini 2.5 Flash: быстрая генерация.'}
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Maximize2" size={20} className="text-secondary" />
                Формат изображения
              </Label>
              <select
                value={aspectRatio}
                onChange={(e) => setAspectRatio(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {aspectRatios.map(ar => (
                  <option key={ar.value} value={ar.value}>{ar.label}</option>
                ))}
              </select>
              {selectedAspectData && (
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>📐 Размер: {selectedAspectData.size}</p>
                  <p>📱 Подходит для: {selectedAspectData.description}</p>
                </div>
              )}
            </div>

            <Button
              onClick={generateImage}
              disabled={isGenerating}
              size="lg"
              className="w-full h-14 text-lg font-bold bg-gradient-to-r from-secondary to-accent hover:opacity-90 transition-all duration-300 shadow-lg hover:shadow-xl"
            >
              {isGenerating ? (
                <>
                  <Icon name="Loader2" size={24} className="animate-spin mr-2" />
                  Создаю изображение...
                </>
              ) : (
                <>
                  <Icon name="Sparkles" size={24} className="mr-2" />
                  Создать изображение
                </>
              )}
            </Button>
          </Card>

          <Card className="md:col-span-3 p-6 space-y-4 shadow-xl border-2 hover:border-primary/50 transition-all duration-300">
            <div className="flex items-center justify-between">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Image" size={20} className="text-primary" />
                Результат
              </Label>
              {generatedImageUrl && (
                <Button
                  onClick={downloadImage}
                  variant="outline"
                  size="sm"
                  className="gap-2"
                >
                  <Icon name="Download" size={16} />
                  Скачать
                </Button>
              )}
            </div>

            <div className="min-h-[600px] bg-muted/30 rounded-lg p-6 relative flex items-center justify-center">
              {!generatedImageUrl && !isGenerating && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6">
                  <div className="text-6xl mb-4 animate-bounce">🖼️</div>
                  <p className="text-xl font-semibold text-muted-foreground mb-2">
                    Ваше изображение появится здесь
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Опишите желаемое изображение и нажмите "Создать"
                  </p>
                </div>
              )}

              {isGenerating && (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Icon name="Sparkles" size={64} className="text-secondary animate-pulse mb-4" />
                  <p className="text-lg font-semibold text-secondary animate-pulse">
                    Рисую идеальное изображение...
                  </p>
                </div>
              )}

              {generatedImageUrl && (
                <div className="w-full h-full flex items-center justify-center animate-fade-in">
                  <img
                    src={generatedImageUrl}
                    alt="Generated image"
                    className="max-w-full max-h-full rounded-lg shadow-2xl object-contain"
                  />
                </div>
              )}
            </div>
          </Card>
        </div>

        <div className="text-center text-sm text-muted-foreground">
          <p className="flex items-center justify-center gap-2">
            Powered by
            <span className="font-semibold bg-gradient-to-r from-secondary to-accent bg-clip-text text-transparent">
              Gemini 2.5 Flash Image
            </span>
            ✨
          </p>
        </div>
      </div>
    </div>
  );
}