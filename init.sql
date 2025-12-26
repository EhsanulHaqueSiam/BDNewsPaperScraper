# PostgreSQL initialization script for BDNewsPaper
# Executed automatically when PostgreSQL container starts

-- Create articles table
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    paper_name VARCHAR(255) NOT NULL,
    headline TEXT NOT NULL,
    sub_title TEXT,
    article_body TEXT,
    author VARCHAR(255),
    category VARCHAR(100),
    keywords TEXT,
    image_url TEXT,
    publication_date TIMESTAMP,
    modification_date TIMESTAMP,
    source_language VARCHAR(10) DEFAULT 'en',
    detected_language VARCHAR(10),
    word_count INTEGER,
    reading_time_minutes INTEGER,
    content_hash VARCHAR(64),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_articles_paper ON articles(paper_name);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(publication_date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_scraped ON articles(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_language ON articles(source_language);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_articles_headline_fts ON articles USING gin(to_tsvector('english', headline));
CREATE INDEX IF NOT EXISTS idx_articles_body_fts ON articles USING gin(to_tsvector('english', article_body));

-- Bookmarks table for dashboard
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    user_id VARCHAR(255) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, user_id)
);

-- Scrape logs for monitoring
CREATE TABLE IF NOT EXISTS scrape_logs (
    id SERIAL PRIMARY KEY,
    spider_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    items_scraped INTEGER DEFAULT 0,
    items_dropped INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',
    log_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_scrape_logs_spider ON scrape_logs(spider_name);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_started ON scrape_logs(started_at DESC);

-- Cache for API responses
CREATE TABLE IF NOT EXISTS api_cache (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at);

-- Stats materialized view for dashboard
CREATE MATERIALIZED VIEW IF NOT EXISTS article_stats AS
SELECT 
    paper_name,
    category,
    source_language,
    DATE(publication_date) as date,
    COUNT(*) as article_count,
    AVG(word_count) as avg_word_count
FROM articles
WHERE publication_date IS NOT NULL
GROUP BY paper_name, category, source_language, DATE(publication_date);

CREATE UNIQUE INDEX IF NOT EXISTS idx_article_stats ON article_stats(paper_name, category, source_language, date);

-- Function to refresh stats
CREATE OR REPLACE FUNCTION refresh_article_stats()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY article_stats;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to refresh stats (optional, can be slow)
-- CREATE TRIGGER trigger_refresh_stats
-- AFTER INSERT OR UPDATE OR DELETE ON articles
-- FOR EACH STATEMENT
-- EXECUTE FUNCTION refresh_article_stats();

-- Utility functions
CREATE OR REPLACE FUNCTION search_articles(search_query TEXT, limit_count INTEGER DEFAULT 20)
RETURNS TABLE(id INTEGER, headline TEXT, paper_name VARCHAR, rank REAL) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.headline,
        a.paper_name,
        ts_rank(to_tsvector('english', a.headline || ' ' || COALESCE(a.article_body, '')), 
                plainto_tsquery('english', search_query)) as rank
    FROM articles a
    WHERE to_tsvector('english', a.headline || ' ' || COALESCE(a.article_body, '')) 
          @@ plainto_tsquery('english', search_query)
    ORDER BY rank DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bdnews;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bdnews;
