import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import Icon from '@/components/ui/icon';

export default function Index() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [platform, setPlatform] = useState('telegram');
  const [task, setTask] = useState('');
  const [tone, setTone] = useState('anya_vibe');
  const [goal, setGoal] = useState('вовлечение');
  const [length, setLength] = useState('средний');
  const [emojis, setEmojis] = useState('баланс');
  const [generatedPost, setGeneratedPost] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const generatePost = async () => {
    if (!task.trim()) {
      toast({
        title: 'Ошибка',
        description: 'Опишите, что хотите получить от поста',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    setGeneratedPost('');

    try {
      const response = await fetch('https://functions.yandexcloud.net/d4env6absccceb6td886', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          platform,
          task,
          tone,
          goal,
          length,
          emojis
        }),
      });

      const data = await response.json();
      
      if (response.ok && data.post) {
        setGeneratedPost(data.post);
        toast({
          title: 'Готово! 🎉',
          description: 'Пост успешно создан',
        });
      } else {
        throw new Error(data.error || 'Не удалось получить ответ');
      }
    } catch (error) {
      toast({
        title: 'Ошибка генерации',
        description: 'Не удалось создать пост. Попробуйте еще раз.',
        variant: 'destructive',
      });
      console.error(error);
    } finally {
      setIsGenerating(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedPost);
    toast({
      title: 'Скопировано! 📋',
      description: 'Пост скопирован в буфер обмена',
    });
  };

  const createImagePrompt = () => {
    if (!generatedPost) return;
    
    const imagePrompt = `Создай иллюстрацию для поста: ${generatedPost.slice(0, 200)}`;
    navigate('/images', { state: { initialPrompt: imagePrompt } });
    
    toast({
      title: 'Переход к генерации! 🎨',
      description: 'Промпт подготовлен для создания изображения',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-primary to-secondary rounded-full shadow-lg">
            <span className="text-3xl">✨</span>
            <h1 className="text-2xl md:text-3xl font-bold text-white">AnyaGPT Generator</h1>
            <span className="text-3xl">✨</span>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Создавайте идеальные посты для соцсетей с помощью AI
          </p>
          <div className="flex gap-4 justify-center">
            <Button variant="default" size="lg" className="font-semibold">
              📝 Текст постов
            </Button>
            <Link to="/images">
              <Button variant="outline" size="lg" className="font-semibold">
                🎨 Изображения
              </Button>
            </Link>
            <Link to="/documents">
              <Button variant="outline" size="lg" className="font-semibold">
                📚 Документы
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card className="p-6 space-y-6 shadow-xl border-2 hover:border-primary/50 transition-all duration-300">
            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="MessageSquare" size={20} className="text-primary" />
                Платформа
              </Label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="telegram">📱 Telegram</option>
                <option value="vk">🔵 ВКонтакте</option>
                <option value="instagram">📸 Instagram</option>
                <option value="facebook">👥 Facebook</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Target" size={20} className="text-primary" />
                Задача поста
              </Label>
              <Textarea
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="Опишите, что хотите получить от текста..."
                className="min-h-[120px] resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Smile" size={20} className="text-primary" />
                Тон поста
              </Label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="anya_vibe">🎓✨ Anya Vibe (фирменный стиль)</option>
                <option value="дружелюбный">😊 Дружелюбный</option>
                <option value="профессиональный">💼 Профессиональный</option>
                <option value="вдохновляющий">🌟 Вдохновляющий</option>
                <option value="юмористический">😄 Юмористический</option>
                <option value="информационный">📚 Информационный</option>
                <option value="провокационный">🔥 Провокационный</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Crosshair" size={20} className="text-primary" />
                Цель поста
              </Label>
              <select
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="вовлечение">💬 Вовлечение</option>
                <option value="продажа">💰 Продажа</option>
                <option value="информирование">📢 Информирование</option>
                <option value="развлечение">🎉 Развлечение</option>
                <option value="обучение">🎓 Обучение</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="AlignLeft" size={20} className="text-primary" />
                Длина поста
              </Label>
              <select
                value={length}
                onChange={(e) => setLength(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="короткий">⚡ Короткий</option>
                <option value="средний">📝 Средний</option>
                <option value="длинный">📄 Длинный</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="Sparkles" size={20} className="text-primary" />
                Количество эмодзи
              </Label>
              <select
                value={emojis}
                onChange={(e) => setEmojis(e.target.value)}
                className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="нет">🚫 Без эмодзи</option>
                <option value="мало">🙂 Мало</option>
                <option value="баланс">✨ Баланс</option>
                <option value="много">🎨 Супер много</option>
              </select>
            </div>

            <Button
              onClick={generatePost}
              disabled={isGenerating}
              size="lg"
              className="w-full h-14 text-lg font-bold bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-all duration-300 shadow-lg hover:shadow-xl"
            >
              {isGenerating ? (
                <>
                  <Icon name="Loader2" size={24} className="animate-spin mr-2" />
                  Генерирую...
                </>
              ) : (
                <>
                  <Icon name="Wand2" size={24} className="mr-2" />
                  Создать пост
                </>
              )}
            </Button>
          </Card>

          <Card className="p-6 space-y-4 shadow-xl border-2 hover:border-secondary/50 transition-all duration-300">
            <div className="flex items-center justify-between">
              <Label className="text-lg font-semibold flex items-center gap-2">
                <Icon name="FileText" size={20} className="text-secondary" />
                Результат
              </Label>
              {generatedPost && (
                <div className="flex gap-2">
                  <Button
                    onClick={copyToClipboard}
                    variant="outline"
                    size="sm"
                    className="gap-2"
                  >
                    <Icon name="Copy" size={16} />
                    Копировать
                  </Button>
                  <Button
                    onClick={createImagePrompt}
                    variant="default"
                    size="sm"
                    className="gap-2"
                  >
                    <Icon name="Image" size={16} />
                    Создать картинку
                  </Button>
                </div>
              )}
            </div>

            <div className="min-h-[600px] bg-muted/30 rounded-lg p-6 relative">
              {!generatedPost && !isGenerating && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6">
                  <div className="text-6xl mb-4 animate-bounce">🎨</div>
                  <p className="text-xl font-semibold text-muted-foreground mb-2">
                    Ваш пост появится здесь
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Заполните параметры и нажмите "Создать пост"
                  </p>
                </div>
              )}

              {isGenerating && (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Icon name="Sparkles" size={64} className="text-primary animate-pulse mb-4" />
                  <p className="text-lg font-semibold text-primary animate-pulse">
                    Создаю идеальный пост...
                  </p>
                </div>
              )}

              {generatedPost && (
                <div className="whitespace-pre-wrap text-base leading-relaxed animate-fade-in">
                  {generatedPost}
                </div>
              )}
            </div>
          </Card>
        </div>

        <div className="text-center text-sm text-muted-foreground">
          <p className="flex items-center justify-center gap-2">
            Powered by
            <span className="font-semibold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Gemini 2.5 Flash
            </span>
            ⚡
          </p>
        </div>
      </div>
    </div>
  );
}