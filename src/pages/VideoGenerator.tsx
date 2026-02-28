import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import Icon from '@/components/ui/icon';

const GEMINI_KEY_STORAGE = 'gemini_api_key_video';

const videoAspectRatios = [
  { value: '16:9', label: '◻️ 16:9 Горизонтальный', description: 'YouTube, экран' },
  { value: '9:16', label: '▭ 9:16 Вертикальный', description: 'Stories, Reels' },
  { value: '1:1', label: '◼️ 1:1 Квадрат', description: 'Соцсети' },
];

const durations = [
  { value: 4, label: '4 сек' },
  { value: 6, label: '6 сек' },
  { value: 8, label: '8 сек' },
];

export default function VideoGenerator() {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoUrlRef = useRef<string>('');
  const [prompt, setPrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [durationSec, setDurationSec] = useState(8);
  const [referenceImage, setReferenceImage] = useState<{ mimeType: string; data: string; preview: string } | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatingElapsedSec, setGeneratingElapsedSec] = useState(0);
  const elapsedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [hasGeminiKey, setHasGeminiKey] = useState(false);

  useEffect(() => {
    setHasGeminiKey(!!localStorage.getItem(GEMINI_KEY_STORAGE)?.trim());
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !file.type.startsWith('image/')) {
      toast({
        title: 'Ошибка',
        description: 'Выберите файл изображения (PNG, JPEG, WebP)',
        variant: 'destructive',
      });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.includes(',') ? result.split(',')[1]! : result;
      setReferenceImage({
        mimeType: file.type,
        data: base64,
        preview: result,
      });
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const clearReference = () => {
    setReferenceImage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const saveGeminiKey = () => {
    const key = geminiKeyInput.trim();
    if (!key) {
      toast({ title: 'Введите ключ', variant: 'destructive' });
      return;
    }
    localStorage.setItem(GEMINI_KEY_STORAGE, key);
    setHasGeminiKey(true);
    setGeminiKeyInput('');
    toast({ title: 'Ключ сохранён', description: 'Используется только в этом браузере для генерации видео' });
  };

  const generateVideo = async () => {
    if (!prompt.trim()) {
      toast({ title: 'Ошибка', description: 'Опишите, какое видео хотите получить', variant: 'destructive' });
      return;
    }
    const apiKey = localStorage.getItem(GEMINI_KEY_STORAGE)?.trim();
    if (!apiKey) {
      toast({
        title: 'Нужен API ключ Gemini',
        description: 'Введите ключ ниже и нажмите «Сохранить». Ключ берётся в Google AI Studio.',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    if (videoUrlRef.current) {
      URL.revokeObjectURL(videoUrlRef.current);
      videoUrlRef.current = '';
    }
    setVideoUrl('');
    setGeneratingElapsedSec(0);
    elapsedIntervalRef.current = setInterval(() => setGeneratingElapsedSec((s) => s + 1), 1000);

    try {
      const { GoogleGenAI } = await import(/* @vite-ignore */ '@google/genai');
      const ai = new GoogleGenAI({ apiKey });

      const durationSecFinal = referenceImage ? 8 : durationSec;
      const params: {
        model: string;
        prompt: string;
        config: { numberOfVideos: number; aspectRatio: string; durationSeconds?: number };
        image?: { inlineData?: { mimeType: string; data: string } };
      } = {
        model: 'veo-3.1-generate-preview',
        prompt: prompt.trim(),
        config: {
          numberOfVideos: 1,
          aspectRatio,
          durationSeconds: durationSecFinal,
        },
      };
      if (referenceImage) {
        params.image = { inlineData: { mimeType: referenceImage.mimeType, data: referenceImage.data } };
      }

      let operation = await ai.models.generateVideos(params as never);

      while (!operation.done) {
        await new Promise((r) => setTimeout(r, 10000));
        operation = await ai.operations.getVideosOperation({ operation });
      }

      const resp = operation.response as { generatedVideos?: Array<{ video?: { uri?: string } }> } | undefined;
      const uri = resp?.generatedVideos?.[0]?.video?.uri;
      if (!uri) {
        throw new Error((operation as { error?: string }).error || 'Нет видео в ответе');
      }

      const downloadUrl = uri + (uri.includes('?') ? '&' : '?') + 'key=' + encodeURIComponent(apiKey);
      const res = await fetch(downloadUrl);
      if (!res.ok) throw new Error('Не удалось скачать видео');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      videoUrlRef.current = url;
      setVideoUrl(url);
      toast({ title: 'Готово! 🎬', description: 'Видео создано' });
    } catch (e) {
      toast({
        title: 'Ошибка генерации',
        description: e instanceof Error ? e.message : 'Не удалось создать видео. Попробуйте позже.',
        variant: 'destructive',
      });
      console.error(e);
    } finally {
      if (elapsedIntervalRef.current) {
        clearInterval(elapsedIntervalRef.current);
        elapsedIntervalRef.current = null;
      }
      setGeneratingElapsedSec(0);
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5 p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-secondary to-accent rounded-full shadow-lg">
            <span className="text-3xl">🎬</span>
            <h1 className="text-2xl md:text-3xl font-bold text-white">Veo 3 — генерация видео</h1>
            <span className="text-3xl">📹</span>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Создавайте короткие видео по текстовому описанию с помощью Google Veo 3
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to="/">
              <Button variant="outline" size="lg" className="font-semibold">
                📝 Текст постов
              </Button>
            </Link>
            <Link to="/images">
              <Button variant="outline" size="lg" className="font-semibold">
                🎨 Изображения
              </Button>
            </Link>
            <Link to="/images-for-anya">
              <Button variant="outline" size="lg" className="font-semibold">
                👗 Образы для Ани
              </Button>
            </Link>
            <Button variant="default" size="lg" className="font-semibold">
              🎬 Видео
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
                <Icon name="Lock" size={20} className="text-secondary" />
                Свой API ключ Gemini (для видео)
              </Label>
              <p className="text-xs text-muted-foreground">
                Ключ берётся в{' '}
                <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="underline">
                  Google AI Studio
                </a>
                . Хранится только в этом браузере, запросы идут напрямую в Google.
              </p>
              {hasGeminiKey ? (
                <p className="text-sm text-green-600 dark:text-green-400">✓ Ключ сохранён</p>
              ) : (
                <div className="flex gap-2">
                  <Input
                    type="password"
                    placeholder="AIza..."
                    value={geminiKeyInput}
                    onChange={(e) => setGeminiKeyInput(e.target.value)}
                    className="flex-1"
                  />
                  <Button type="button" variant="secondary" onClick={saveGeminiKey}>
                    Сохранить
                  </Button>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Image" size={20} className="text-secondary" />
                Картинка-образец (опционально)
              </Label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={onFileChange}
                className="hidden"
              />
              {!referenceImage ? (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="min-h-[100px] border-2 border-dashed border-muted-foreground/30 rounded-lg flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-secondary/50 hover:bg-muted/30 transition-colors"
                >
                  <Icon name="Upload" size={32} className="text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Добавить изображение для видео по кадру</span>
                  <span className="text-xs text-muted-foreground">PNG, JPEG, WebP</span>
                </div>
              ) : (
                <div className="relative rounded-lg overflow-hidden border-2 border-border">
                  <img
                    src={referenceImage.preview}
                    alt="Образец"
                    className="w-full h-auto max-h-[180px] object-contain bg-muted/30"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={clearReference}
                  >
                    ✕ Убрать
                  </Button>
                </div>
              )}
              {referenceImage && (
                <p className="text-xs text-muted-foreground">
                  Видео будет создано на основе этого кадра. Длительность при этом — 8 сек.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Wand2" size={20} className="text-secondary" />
                Описание видео
              </Label>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Опишите сцену: что происходит, кто в кадре, настроение, стиль..."
                className="min-h-[120px] resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Maximize2" size={20} className="text-secondary" />
                Соотношение сторон
              </Label>
              <select
                value={aspectRatio}
                onChange={(e) => setAspectRatio(e.target.value)}
                className="flex h-12 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {videoAspectRatios.map((ar) => (
                  <option key={ar.value} value={ar.value}>{ar.label}</option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                {videoAspectRatios.find((ar) => ar.value === aspectRatio)?.description}
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Clock" size={20} className="text-secondary" />
                Длительность
              </Label>
              <select
                value={referenceImage ? 8 : durationSec}
                onChange={(e) => setDurationSec(Number(e.target.value))}
                disabled={!!referenceImage}
                className="flex h-12 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-70"
              >
                {durations.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
              {referenceImage && (
                <p className="text-xs text-muted-foreground">Для видео по картинке доступна только 8 сек.</p>
              )}
            </div>

            <Button
              onClick={generateVideo}
              disabled={isGenerating || !hasGeminiKey}
              size="lg"
              className="w-full h-14 text-lg font-bold bg-gradient-to-r from-secondary to-accent hover:opacity-90 transition-all duration-300 shadow-lg"
            >
              {isGenerating ? (
                <>
                  <Icon name="Loader2" size={24} className="animate-spin mr-2" />
                  Создаю видео...
                </>
              ) : (
                <>
                  <Icon name="Video" size={24} className="mr-2" />
                  Создать видео
                </>
              )}
            </Button>
            {!hasGeminiKey && (
              <p className="text-xs text-amber-600">Сначала введите и сохраните API ключ Gemini выше.</p>
            )}
          </Card>

          <Card className="md:col-span-3 p-6 space-y-4 shadow-xl border-2 hover:border-primary/50 transition-all duration-300">
            <Label className="text-lg font-semibold flex items-center gap-2">
              <Icon name="Video" size={20} className="text-primary" />
              Результат
            </Label>
            <div className="min-h-[400px] bg-muted/30 rounded-lg flex items-center justify-center">
              {!videoUrl && !isGenerating && (
                <div className="text-center text-muted-foreground p-6">
                  <p className="text-xl mb-2">🎬</p>
                  <p>Видео появится здесь после генерации</p>
                </div>
              )}
              {isGenerating && (
                <div className="flex flex-col items-center gap-4">
                  <Icon name="Loader2" size={48} className="animate-spin text-secondary" />
                  <p className="text-secondary font-medium">Генерация видео обычно занимает 1–3 минуты</p>
                  <p className="text-sm text-muted-foreground">Прошло {generatingElapsedSec} сек</p>
                </div>
              )}
              {videoUrl && (
                <div className="space-y-3">
                  <video
                    src={videoUrl}
                    controls
                    className="max-w-full max-h-[70vh] rounded-lg"
                    playsInline
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const a = document.createElement('a');
                      a.href = videoUrl;
                      a.download = 'veo-video.mp4';
                      a.click();
                    }}
                    className="flex items-center gap-2"
                  >
                    <Icon name="Download" size={18} />
                    Скачать видео
                  </Button>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
