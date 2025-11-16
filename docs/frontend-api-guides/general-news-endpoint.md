# General News Endpoint

## Overview
This endpoint retrieves general market news that is not ticker-specific. It provides the latest financial news from various sources to keep users informed about market developments.

## Endpoint Details

**URL:** `GET /api/news/general`

**Authentication:** Required (API Key via `X-API-Key` header)

**Tags:** News & Media 📰

## Request Parameters

### Query Parameters

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `limit` | integer | No | 1000 | 1-1000 | Maximum number of news items to return |

## Response Format

### Success Response (200 OK)

```json
{
  "status": 200,
  "message": "General news retrieved successfully",
  "data": {
    "kind": "news#general",
    "selfLink": "/api/news/general?limit=100",
    "totalItems": 100,
    "currentItemCount": 100,
    "payload": [
      {
        "title": "Market Analysis: Tech Stocks Rally",
        "site": "Bloomberg",
        "publishedDate": "2025-01-15T14:30:00Z",
        "text": "Full article text...",
        "url": "https://example.com/article",
        "image": "https://example.com/image.jpg"
      }
    ]
  }
}
```

### Error Response (500 Internal Server Error)

```json
{
  "error": {
    "code": 500,
    "message": "Failed to retrieve general news from FMP API"
  }
}
```

## Frontend Implementation

### TypeScript/JavaScript Example

```typescript
// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';
const API_KEY = 'your-api-key-here';

// Type Definitions
interface NewsItem {
  title: string;
  site: string;
  publishedDate: string;
  text: string;
  url: string;
  image?: string;
}

interface GeneralNewsResponse {
  status: number;
  message: string;
  data: {
    kind: string;
    selfLink: string;
    totalItems: number;
    currentItemCount: number;
    payload: NewsItem[];
  };
}

// Fetch General News Function
async function fetchGeneralNews(limit: number = 100): Promise<NewsItem[]> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/news/general?limit=${limit}`,
      {
        method: 'GET',
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: GeneralNewsResponse = await response.json();
    return data.data.payload;
  } catch (error) {
    console.error('Error fetching general news:', error);
    throw error;
  }
}

// Usage Example
async function displayGeneralNews() {
  try {
    const newsItems = await fetchGeneralNews(50);

    console.log(`Fetched ${newsItems.length} news items`);

    // Render news items in your UI
    newsItems.forEach(item => {
      console.log(`${item.title} - ${item.site}`);
    });
  } catch (error) {
    // Handle error in UI
    console.error('Failed to load news:', error);
  }
}
```

### React Component Example

```tsx
import React, { useState, useEffect } from 'react';

interface NewsItem {
  title: string;
  site: string;
  publishedDate: string;
  text: string;
  url: string;
  image?: string;
}

const GeneralNewsComponent: React.FC = () => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          'http://localhost:8000/api/news/general?limit=20',
          {
            headers: {
              'X-API-Key': process.env.REACT_APP_API_KEY || '',
            },
          }
        );

        if (!response.ok) throw new Error('Failed to fetch news');

        const data = await response.json();
        setNews(data.data.payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  if (loading) return <div>Loading news...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="general-news">
      <h2>Latest Market News</h2>
      <div className="news-grid">
        {news.map((item, index) => (
          <div key={index} className="news-card">
            {item.image && <img src={item.image} alt={item.title} />}
            <h3>{item.title}</h3>
            <p className="source">{item.site}</p>
            <p className="date">
              {new Date(item.publishedDate).toLocaleDateString()}
            </p>
            <p className="excerpt">{item.text.substring(0, 150)}...</p>
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              Read More
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};

export default GeneralNewsComponent;
```

### Vue.js Example

```vue
<template>
  <div class="general-news">
    <h2>Latest Market News</h2>

    <div v-if="loading">Loading news...</div>
    <div v-else-if="error">Error: {{ error }}</div>

    <div v-else class="news-grid">
      <div v-for="(item, index) in newsItems" :key="index" class="news-card">
        <img v-if="item.image" :src="item.image" :alt="item.title" />
        <h3>{{ item.title }}</h3>
        <p class="source">{{ item.site }}</p>
        <p class="date">{{ formatDate(item.publishedDate) }}</p>
        <p class="excerpt">{{ item.text.substring(0, 150) }}...</p>
        <a :href="item.url" target="_blank" rel="noopener noreferrer">
          Read More
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface NewsItem {
  title: string;
  site: string;
  publishedDate: string;
  text: string;
  url: string;
  image?: string;
}

const newsItems = ref<NewsItem[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString();
};

const fetchGeneralNews = async () => {
  try {
    loading.value = true;
    const response = await fetch(
      'http://localhost:8000/api/news/general?limit=20',
      {
        headers: {
          'X-API-Key': import.meta.env.VITE_API_KEY || '',
        },
      }
    );

    if (!response.ok) throw new Error('Failed to fetch news');

    const data = await response.json();
    newsItems.value = data.data.payload;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error';
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchGeneralNews();
});
</script>
```

## Best Practices

### 1. **Pagination**
For displaying large amounts of news, implement client-side pagination:

```typescript
const NEWS_PER_PAGE = 10;

function paginateNews(news: NewsItem[], page: number): NewsItem[] {
  const start = page * NEWS_PER_PAGE;
  const end = start + NEWS_PER_PAGE;
  return news.slice(start, end);
}
```

### 2. **Caching**
Cache news data to reduce API calls:

```typescript
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

let newsCache: { data: NewsItem[]; timestamp: number } | null = null;

async function fetchGeneralNewsWithCache(limit: number = 100): Promise<NewsItem[]> {
  const now = Date.now();

  if (newsCache && now - newsCache.timestamp < CACHE_DURATION) {
    return newsCache.data;
  }

  const data = await fetchGeneralNews(limit);
  newsCache = { data, timestamp: now };

  return data;
}
```

### 3. **Error Handling**
Implement robust error handling:

```typescript
async function fetchGeneralNewsWithRetry(
  limit: number = 100,
  maxRetries: number = 3
): Promise<NewsItem[]> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fetchGeneralNews(limit);
    } catch (error) {
      if (attempt === maxRetries) throw error;

      // Exponential backoff
      const delay = Math.pow(2, attempt) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw new Error('Max retries exceeded');
}
```

### 4. **Loading States**
Provide clear feedback to users:

```typescript
enum LoadingState {
  IDLE = 'idle',
  LOADING = 'loading',
  SUCCESS = 'success',
  ERROR = 'error'
}

// Use in your component state management
```

### 5. **Limit Optimization**
Request only what you need:

```typescript
// For a news feed widget, request fewer items
const widgetNews = await fetchGeneralNews(5);

// For a dedicated news page, request more items
const pageNews = await fetchGeneralNews(100);
```

## Common Use Cases

### 1. **News Feed Widget**
Display recent news on a dashboard:

```typescript
async function renderNewsFeedWidget() {
  const news = await fetchGeneralNews(5);
  const widget = document.getElementById('news-widget');

  widget.innerHTML = news
    .map(item => `
      <div class="news-item">
        <h4>${item.title}</h4>
        <span>${item.site}</span>
      </div>
    `)
    .join('');
}
```

### 2. **Infinite Scroll**
Load more news as user scrolls:

```typescript
let currentBatch = 0;
const BATCH_SIZE = 20;

async function loadMoreNews() {
  const allNews = await fetchGeneralNews(1000);
  const start = currentBatch * BATCH_SIZE;
  const end = start + BATCH_SIZE;

  return allNews.slice(start, end);
}
```

### 3. **Search/Filter**
Filter news by keywords:

```typescript
function filterNews(news: NewsItem[], keyword: string): NewsItem[] {
  const lowerKeyword = keyword.toLowerCase();

  return news.filter(item =>
    item.title.toLowerCase().includes(lowerKeyword) ||
    item.text.toLowerCase().includes(lowerKeyword)
  );
}
```

## Notes

- **Rate Limiting**: The API may have rate limits. Implement appropriate throttling in production.
- **Image Handling**: Some news items may not have images. Always check before rendering.
- **Date Formatting**: Published dates are in ISO 8601 format. Format them appropriately for your locale.
- **External Links**: News URLs point to external sources. Consider opening them in new tabs.
- **Content Length**: News text can be very long. Truncate for preview displays.

## Related Endpoints

- `GET /api/news/{ticker}/stock-news` - Get ticker-specific news
- `GET /api/news/fmp-articles` - Get FMP original articles
- `GET /api/news/{ticker}/press-releases` - Get company press releases
