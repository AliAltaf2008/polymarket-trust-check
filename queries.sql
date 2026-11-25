.headers on
.mode column


-- Query 1: The 10 markets with the most trading volume
SELECT question, volume
FROM markets
ORDER BY volume DESC
LIMIT 10;


--Query 2: How many markets each event has and their average volume

SELECT event_id,
       COUNT(*) AS market_count,
       ROUND(AVG(volume)) AS avg_volume
FROM markets
GROUP BY event_id
ORDER BY market_count DESC, avg_volume DESC
LIMIT 10;