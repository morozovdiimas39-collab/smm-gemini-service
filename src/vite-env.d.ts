/// <reference types="vite/client" />

declare module '@google/genai' {
  export class GoogleGenAI {
    constructor(options: { apiKey: string });
    models: { generateVideos: (params: unknown) => Promise<unknown> };
    operations: { getVideosOperation: (params: { operation: unknown }) => Promise<unknown> };
  }
}
