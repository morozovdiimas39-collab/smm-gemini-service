import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import Icon from '@/components/ui/icon';

interface Topic {
  title: string;
  description: string;
}

export default function Documents() {
  const { toast } = useToast();
  const [docType, setDocType] = useState('реферат');
  const [subject, setSubject] = useState('');
  const [pages, setPages] = useState(10);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [qualityLevel, setQualityLevel] = useState<'standard' | 'high' | 'max'>('high');
  const [topics, setTopics] = useState<Topic[]>([]);
  const [isGeneratingTopics, setIsGeneratingTopics] = useState(false);
  const [isGeneratingDocument, setIsGeneratingDocument] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generatedDocument, setGeneratedDocument] = useState('');
  const [qualityScore, setQualityScore] = useState<{ai_score: number, uniqueness_score: number, attempts: number, passed: boolean} | null>(null);

  const generateTopics = async () => {
    if (!subject.trim()) {
      toast({
        title: 'Ошибка',
        description: 'Укажите тему документа',
        variant: 'destructive',
      });
      return;
    }

    setIsGeneratingTopics(true);
    setTopics([]);
    setGeneratedDocument('');

    try {
      const response = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'topics',
          docType,
          subject,
          pages,
          additionalInfo
        }),
      });

      const data = await response.json();
      
      if (response.ok && data.topics) {
        setTopics(data.topics);
        toast({
          title: 'Готово! 📋',
          description: 'Темы сгенерированы. Отредактируйте при необходимости.',
        });
      } else {
        throw new Error(data.error || 'Не удалось получить темы');
      }
    } catch (error) {
      toast({
        title: 'Ошибка генерации',
        description: 'Не удалось сгенерировать темы. Попробуйте еще раз.',
        variant: 'destructive',
      });
      console.error(error);
    } finally {
      setIsGeneratingTopics(false);
    }
  };

  const updateTopic = (index: number, field: 'title' | 'description', value: string) => {
    const newTopics = [...topics];
    newTopics[index][field] = value;
    setTopics(newTopics);
  };

  const removeTopic = (index: number) => {
    const newTopics = topics.filter((_, i) => i !== index);
    setTopics(newTopics);
    toast({
      title: 'Удалено',
      description: 'Тема удалена из структуры',
    });
  };

  const generateDocument = async () => {
    if (topics.length === 0) {
      toast({
        title: 'Ошибка',
        description: 'Сначала сгенерируйте темы',
        variant: 'destructive',
      });
      return;
    }

    setIsGeneratingDocument(true);
    setGeneratedDocument('');
    setGenerationProgress(0);

    try {
      let fullDocument = `${docType.toUpperCase()}\n\nТема: ${subject}\n\n`;
      let introText = '';
      
      fullDocument += 'ВВЕДЕНИЕ\n\n';
      try {
        const introResponse = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mode: 'section',
            docType,
            subject,
            pages,
            topics,
            sectionTitle: 'Введение',
            sectionDescription: `Введение к ${docType} на тему "${subject}"`,
            additionalInfo,
            qualityLevel
          }),
        });
        const introData = await introResponse.json();
        if (introResponse.ok && introData.text) {
          introText = introData.text;
          fullDocument += introText + '\n\n';
          setGeneratedDocument(fullDocument);
        } else {
          introText = `[Ошибка генерации введения]`;
          fullDocument += introText + '\n\n';
          setGeneratedDocument(fullDocument);
        }
        if (introData.quality) {
          setQualityScore(introData.quality);
        }
      } catch (err) {
        console.error('Ошибка генерации введения:', err);
        introText = `[Ошибка генерации введения]`;
        fullDocument += introText + '\n\n';
        setGeneratedDocument(fullDocument);
      }
      setGenerationProgress(Math.floor((1 / (topics.length + 2)) * 100));

      for (let i = 0; i < topics.length; i++) {
        const topic = topics[i];
        fullDocument += `${i + 1}. ${topic.title.toUpperCase()}\n\n`;
        
        let retryCount = 0;
        const maxRetries = 3;
        let success = false;
        
        while (retryCount < maxRetries && !success) {
          try {
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            const sectionResponse = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                mode: 'section',
                docType,
                subject,
                pages,
                topics,
                sectionTitle: topic.title,
                sectionDescription: topic.description,
                additionalInfo,
                qualityLevel
              }),
            });
            
            const sectionData = await sectionResponse.json();
            if (sectionResponse.ok && sectionData.text) {
              fullDocument += sectionData.text + '\n\n';
              setGeneratedDocument(fullDocument);
              success = true;
            } else if (sectionResponse.status === 429 || sectionResponse.status === 500) {
              retryCount++;
              if (retryCount >= maxRetries) {
                fullDocument += `[Ошибка генерации раздела - превышен лимит запросов]\n\n`;
                setGeneratedDocument(fullDocument);
              }
            } else {
              fullDocument += `[Ошибка генерации раздела]\n\n`;
              setGeneratedDocument(fullDocument);
              success = true;
            }
            if (sectionData.quality) {
              setQualityScore(sectionData.quality);
            }
          } catch (err) {
            console.error(`Ошибка генерации раздела ${i + 1}:`, err);
            retryCount++;
            if (retryCount >= maxRetries) {
              fullDocument += `[Ошибка генерации раздела]\n\n`;
              setGeneratedDocument(fullDocument);
            }
          }
        }
        
        setGenerationProgress(Math.floor(((i + 2) / (topics.length + 2)) * 100));
      }

      fullDocument += 'ЗАКЛЮЧЕНИЕ\n\n';
      try {
        const conclusionResponse = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mode: 'section',
            docType,
            subject,
            pages,
            topics,
            sectionTitle: 'Заключение',
            sectionDescription: `Заключение к ${docType} на тему "${subject}"`,
            additionalInfo,
            qualityLevel
          }),
        });
        const conclusionData = await conclusionResponse.json();
        if (conclusionResponse.ok && conclusionData.text) {
          fullDocument += conclusionData.text + '\n\n';
          setGeneratedDocument(fullDocument);
        } else {
          fullDocument += `[Ошибка генерации заключения]\n\n`;
          setGeneratedDocument(fullDocument);
        }
        if (conclusionData.quality) {
          setQualityScore(conclusionData.quality);
        }
      } catch (err) {
        console.error('Ошибка генерации заключения:', err);
        fullDocument += `[Ошибка генерации заключения]\n\n`;
        setGeneratedDocument(fullDocument);
      }
      
      setGenerationProgress(100);
      toast({
        title: 'Готово! 🎉',
        description: 'Документ успешно создан',
      });
    } catch (error) {
      toast({
        title: 'Ошибка генерации',
        description: 'Не удалось создать документ. Попробуйте еще раз.',
        variant: 'destructive',
      });
      console.error(error);
    } finally {
      setIsGeneratingDocument(false);
      setGenerationProgress(0);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedDocument);
    toast({
      title: 'Скопировано! 📋',
      description: 'Документ скопирован в буфер обмена',
    });
  };

  const retryFailedSections = async () => {
    if (!generatedDocument) return;
    
    setIsGeneratingDocument(true);
    setGenerationProgress(0);
    
    try {
      toast({
        title: 'Перегенерация ошибок...',
        description: 'Повторная генерация только упавших разделов',
      });
      
      let fullDocument = generatedDocument;
      const errorPattern = /\[Ошибка генерации [^\]]+\]/g;
      const errors = fullDocument.match(errorPattern) || [];
      
      if (errors.length === 0) {
        toast({
          title: 'Нет ошибок',
          description: 'Все разделы сгенерированы успешно',
        });
        setIsGeneratingDocument(false);
        return;
      }
      
      const sections = fullDocument.split(/\n(?=\d+\. [А-ЯЁ]|ВВЕДЕНИЕ|ЗАКЛЮЧЕНИЕ)/);
      let processedCount = 0;
      
      for (let i = 0; i < sections.length; i++) {
        const section = sections[i];
        
        if (section.includes('[Ошибка генерации')) {
          let sectionTitle = '';
          let sectionDescription = '';
          
          if (section.includes('ВВЕДЕНИЕ')) {
            sectionTitle = 'Введение';
            sectionDescription = `Введение к ${docType} на тему "${subject}"`;
          } else if (section.includes('ЗАКЛЮЧЕНИЕ')) {
            sectionTitle = 'Заключение';
            sectionDescription = `Заключение к ${docType} на тему "${subject}"`;
          } else {
            const titleMatch = section.match(/\d+\. ([А-ЯЁ][^\n]+)/);
            if (titleMatch) {
              const topicIndex = parseInt(section.match(/^(\d+)\./)?.[1] || '0') - 1;
              if (topicIndex >= 0 && topicIndex < topics.length) {
                sectionTitle = topics[topicIndex].title;
                sectionDescription = topics[topicIndex].description;
              }
            }
          }
          
          if (sectionTitle) {
            let retryCount = 0;
            const maxRetries = 3;
            let success = false;
            
            while (retryCount < maxRetries && !success) {
              try {
                if (retryCount > 0) {
                  await new Promise(resolve => setTimeout(resolve, 3000 * retryCount));
                }
                
                const response = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    mode: 'section',
                    docType,
                    subject,
                    pages,
                    topics,
                    sectionTitle,
                    sectionDescription,
                    additionalInfo,
                    qualityLevel
                  }),
                });
                
                const data = await response.json();
                if (response.ok && data.text) {
                  sections[i] = section.replace(/\[Ошибка генерации [^\]]+\]/, data.text);
                  fullDocument = sections.join('\n');
                  setGeneratedDocument(fullDocument);
                  success = true;
                } else if (response.status === 429 || response.status === 500) {
                  retryCount++;
                } else {
                  success = true;
                }
              } catch (err) {
                console.error(`Ошибка перегенерации раздела:`, err);
                retryCount++;
              }
            }
            
            processedCount++;
            setGenerationProgress(Math.floor((processedCount / errors.length) * 100));
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
        }
      }
      
      setGenerationProgress(100);
      toast({
        title: 'Готово! ✅',
        description: `Перегенерировано разделов: ${processedCount}`,
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось перегенерировать разделы',
        variant: 'destructive',
      });
      console.error(error);
    } finally {
      setIsGeneratingDocument(false);
      setGenerationProgress(0);
    }
  };

  const improveQuality = async () => {
    if (!generatedDocument) return;
    
    setIsGeneratingDocument(true);
    setGenerationProgress(0);
    
    try {
      toast({
        title: 'Улучшаем качество...',
        description: 'Перегенерируем документ с повышенными требованиями',
      });
      
      let fullDocument = `${docType.toUpperCase()}\n\nТема: ${subject}\n\n`;
      
      fullDocument += 'ВВЕДЕНИЕ\n\n';
      const introResponse = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'section',
          docType,
          subject,
          pages,
          topics,
          sectionTitle: 'Введение',
          sectionDescription: `Введение к ${docType} на тему "${subject}"`,
          additionalInfo,
          qualityLevel: 'max'
        }),
      });
      const introData = await introResponse.json();
      if (introData.text) {
        fullDocument += introData.text + '\n\n';
        setGeneratedDocument(fullDocument);
      }
      if (introData.quality) {
        setQualityScore(introData.quality);
      }
      setGenerationProgress(Math.floor((1 / (topics.length + 2)) * 100));

      for (let i = 0; i < topics.length; i++) {
        const topic = topics[i];
        fullDocument += `${i + 1}. ${topic.title.toUpperCase()}\n\n`;
        
        const sectionResponse = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mode: 'section',
            docType,
            subject,
            pages,
            topics,
            sectionTitle: topic.title,
            sectionDescription: topic.description,
            additionalInfo,
            qualityLevel: 'max'
          }),
        });
        
        const sectionData = await sectionResponse.json();
        if (sectionData.text) {
          fullDocument += sectionData.text + '\n\n';
          setGeneratedDocument(fullDocument);
        }
        if (sectionData.quality) {
          setQualityScore(sectionData.quality);
        }
        
        setGenerationProgress(Math.floor(((i + 2) / (topics.length + 2)) * 100));
      }

      fullDocument += 'ЗАКЛЮЧЕНИЕ\n\n';
      const conclusionResponse = await fetch('https://functions.yandexcloud.net/d4ep127ik5qbfueas45d', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'section',
          docType,
          subject,
          pages,
          topics,
          sectionTitle: 'Заключение',
          sectionDescription: `Заключение к ${docType} на тему "${subject}"`,
          additionalInfo,
          qualityLevel: 'max'
        }),
      });
      const conclusionData = await conclusionResponse.json();
      if (conclusionData.text) {
        fullDocument += conclusionData.text + '\n\n';
        setGeneratedDocument(fullDocument);
      }
      if (conclusionData.quality) {
        setQualityScore(conclusionData.quality);
      }
      
      setGenerationProgress(100);
      toast({
        title: 'Улучшено! ✨',
        description: 'Документ перегенерирован с максимальным качеством',
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось улучшить качество',
        variant: 'destructive',
      });
      console.error(error);
    } finally {
      setIsGeneratingDocument(false);
      setGenerationProgress(0);
    }
  };

  const downloadDocument = () => {
    const blob = new Blob([generatedDocument], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${docType}_${subject.slice(0, 30)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast({
      title: 'Скачано! 💾',
      description: 'Документ сохранен на ваше устройство',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-secondary/5 to-accent/5 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-primary to-secondary rounded-full shadow-lg">
            <span className="text-3xl">📚</span>
            <h1 className="text-2xl md:text-3xl font-bold text-white">AnyaGPT Documents</h1>
            <span className="text-3xl">📝</span>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Создавайте рефераты, курсовые и доклады с помощью AI
          </p>
          <div className="flex gap-4 justify-center">
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
            <Link to="/video">
              <Button variant="outline" size="lg" className="font-semibold">
                🎬 Видео
              </Button>
            </Link>
            <Button variant="default" size="lg" className="font-semibold">
              📚 Документы
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card className="p-6 space-y-6 shadow-xl border-2 hover:border-primary/50 transition-all duration-300">
              <div className="space-y-2">
                <Label className="text-lg font-semibold flex items-center gap-2">
                  <Icon name="FileText" size={20} className="text-primary" />
                  Тип документа
                </Label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value="реферат">📄 Реферат</option>
                  <option value="курсовая">🎓 Курсовая работа</option>
                  <option value="доклад">📢 Доклад</option>
                  <option value="эссе">✍️ Эссе</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label className="text-lg font-semibold flex items-center gap-2">
                  <Icon name="BookOpen" size={20} className="text-primary" />
                  Тема
                </Label>
                <Input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Например: Искусственный интеллект в медицине"
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-lg font-semibold flex items-center gap-2">
                  <Icon name="FileStack" size={20} className="text-primary" />
                  Количество страниц А4
                </Label>
                <div className="flex items-center gap-4">
                  <Input
                    type="number"
                    value={pages}
                    onChange={(e) => setPages(Math.max(1, Math.min(100, parseInt(e.target.value) || 1)))}
                    min="1"
                    max="100"
                    className="h-12 w-24"
                  />
                  <input
                    type="range"
                    value={pages}
                    onChange={(e) => setPages(parseInt(e.target.value))}
                    min="1"
                    max="100"
                    className="flex-1"
                  />
                  <span className="text-sm font-medium w-16 text-right">{pages} стр.</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-lg font-semibold flex items-center gap-2">
                  <Icon name="Sparkles" size={20} className="text-primary" />
                  Уровень качества
                </Label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => setQualityLevel('standard')}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      qualityLevel === 'standard' 
                        ? 'border-green-500 bg-green-50' 
                        : 'border-gray-200 hover:border-green-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">🟢</div>
                    <div className="font-semibold text-sm">Стандарт</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Быстро, AI &lt; 70%
                    </div>
                  </button>
                  
                  <button
                    onClick={() => setQualityLevel('high')}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      qualityLevel === 'high' 
                        ? 'border-yellow-500 bg-yellow-50' 
                        : 'border-gray-200 hover:border-yellow-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">🟡</div>
                    <div className="font-semibold text-sm">Высокое</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Средне, AI &lt; 50%
                    </div>
                  </button>
                  
                  <button
                    onClick={() => setQualityLevel('max')}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      qualityLevel === 'max' 
                        ? 'border-red-500 bg-red-50' 
                        : 'border-gray-200 hover:border-red-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">🔴</div>
                    <div className="font-semibold text-sm">Максимум</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Медленно, AI &lt; 30%
                    </div>
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-lg font-semibold flex items-center gap-2">
                  <Icon name="Info" size={20} className="text-primary" />
                  Дополнительные требования
                </Label>
                <Textarea
                  value={additionalInfo}
                  onChange={(e) => setAdditionalInfo(e.target.value)}
                  placeholder="Укажите специфические требования, источники, акценты..."
                  className="min-h-[100px] resize-none"
                />
              </div>

              <Button 
                onClick={generateTopics}
                disabled={isGeneratingTopics}
                className="w-full h-12 text-lg font-semibold"
                size="lg"
              >
                {isGeneratingTopics ? (
                  <>
                    <Icon name="Loader2" size={20} className="animate-spin mr-2" />
                    Генерирую темы...
                  </>
                ) : (
                  <>
                    <Icon name="Sparkles" size={20} className="mr-2" />
                    Сгенерировать темы
                  </>
                )}
              </Button>
            </Card>

            {topics.length > 0 && (
              <Card className="p-6 space-y-4 shadow-xl border-2 border-primary/50">
                <div className="flex items-center justify-between">
                  <Label className="text-lg font-semibold flex items-center gap-2">
                    <Icon name="List" size={20} className="text-primary" />
                    Структура документа
                  </Label>
                  <span className="text-sm text-muted-foreground">{topics.length} разделов</span>
                </div>
                
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                  {topics.map((topic, index) => (
                    <div key={index} className="space-y-2 p-4 bg-muted/50 rounded-lg relative">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeTopic(index)}
                        className="absolute top-2 right-2 h-8 w-8 p-0 hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Icon name="X" size={16} />
                      </Button>
                      <Input
                        value={topic.title}
                        onChange={(e) => updateTopic(index, 'title', e.target.value)}
                        className="font-semibold"
                        placeholder="Название раздела"
                      />
                      <Textarea
                        value={topic.description}
                        onChange={(e) => updateTopic(index, 'description', e.target.value)}
                        className="text-sm resize-none"
                        rows={2}
                        placeholder="Описание раздела"
                      />
                    </div>
                  ))}
                </div>

                <div className="space-y-2">
                  {isGeneratingDocument && generationProgress > 0 && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Генерирую документ...</span>
                        <span>{generationProgress}%</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div 
                          className="bg-primary h-2 rounded-full transition-all duration-300"
                          style={{ width: `${generationProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                  <Button 
                    onClick={generateDocument}
                    disabled={isGeneratingDocument}
                    className="w-full h-12 text-lg font-semibold"
                    size="lg"
                    variant="default"
                  >
                    {isGeneratingDocument ? (
                      <>
                        <Icon name="Loader2" size={20} className="animate-spin mr-2" />
                        Пишу документ...
                      </>
                    ) : (
                      <>
                        <Icon name="FileEdit" size={20} className="mr-2" />
                        Написать документ
                      </>
                    )}
                  </Button>
                </div>
              </Card>
            )}
          </div>

          {generatedDocument && (
            <div className="lg:sticky lg:top-8 h-fit">
              <Card className="p-6 space-y-4 shadow-xl border-2 border-primary/50">
                <div className="flex items-center justify-between">
                  <Label className="text-lg font-semibold flex items-center gap-2">
                    <Icon name="FileCheck" size={20} className="text-primary" />
                    Готовый документ
                  </Label>
                  <div className="flex gap-2">
                    {generatedDocument.includes('[Ошибка генерации') && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={retryFailedSections}
                        disabled={isGeneratingDocument}
                        className="gap-1"
                      >
                        <Icon name="RefreshCw" size={16} />
                        Исправить ошибки
                      </Button>
                    )}
                    {qualityScore && !qualityScore.passed && (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={improveQuality}
                        disabled={isGeneratingDocument}
                        className="gap-1"
                      >
                        <Icon name="Sparkles" size={16} />
                        Улучшить
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={copyToClipboard}
                    >
                      <Icon name="Copy" size={16} className="mr-1" />
                      Копировать
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={downloadDocument}
                    >
                      <Icon name="Download" size={16} className="mr-1" />
                      Скачать
                    </Button>
                  </div>
                </div>
                
                {qualityScore && (
                  <div className="flex gap-3 p-4 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-lg border border-primary/20">
                    <div className="flex-1 text-center">
                      <div className="text-sm text-muted-foreground mb-1">AI-детекция</div>
                      <div className={`text-2xl font-bold ${
                        qualityScore.ai_score < 50 ? 'text-green-600' : 
                        qualityScore.ai_score < 70 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {qualityScore.ai_score}%
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {qualityScore.ai_score < 50 ? '✅ Естественно' : 
                         qualityScore.ai_score < 70 ? '⚠️ Средне' : '❌ Похоже на AI'}
                      </div>
                    </div>
                    
                    <div className="w-px bg-border"></div>
                    
                    <div className="flex-1 text-center">
                      <div className="text-sm text-muted-foreground mb-1">Уникальность</div>
                      <div className={`text-2xl font-bold ${
                        qualityScore.uniqueness_score > 70 ? 'text-green-600' : 
                        qualityScore.uniqueness_score > 40 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {qualityScore.uniqueness_score}%
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {qualityScore.uniqueness_score > 70 ? '✅ Оригинально' : 
                         qualityScore.uniqueness_score > 40 ? '⚠️ Средне' : '❌ Шаблонно'}
                      </div>
                    </div>
                    
                    <div className="w-px bg-border"></div>
                    
                    <div className="flex-1 text-center">
                      <div className="text-sm text-muted-foreground mb-1">Попытки</div>
                      <div className="text-2xl font-bold text-primary">
                        {qualityScore.attempts}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {qualityScore.passed ? '✅ Прошло' : '⚠️ Не прошло'}
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="bg-muted/50 rounded-lg p-4 max-h-[600px] overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm font-mono">{generatedDocument}</pre>
                </div>

                <div className="text-xs text-muted-foreground text-center">
                  Символов: {generatedDocument.length}
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}