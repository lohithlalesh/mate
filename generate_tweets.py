 #!/usr/bin/env python3                                                                                                                              
  """                                                                                                                                                 
  Simplify Suite - Tweet & Reply Generator                                                                                                            
  Sources : RSS news + Reddit (fully free)                                                                                                            
  Output  : Google Sheets (appends rows directly, serial numbered)                                                                                    
  Tracking: processed_urls.txt in repo (remembers what was already done)                                                                              
  """                                                                                                                                                 
                                                                                                                                                      
  import os                                                                                                                                           
  import re                                                                                                                                           
  import json                                                                                                                                         
  import time                                                                                                                                         
  import urllib.request                                     
  import urllib.parse
  import feedparser
  import gspread
  from google.oauth2.service_account import Credentials
  from datetime import datetime           
  from groq import Groq
                                                                                                                                                      
  # ── Config ────────────────────────────────────────────────────────────────────
                                                                                                                                                      
  GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")   
  SHEETS_CREDENTIALS = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")                                                                                
  SHEET_ID           = os.environ.get("GOOGLE_SHEET_ID", "")
  SHEET_TAB          = "Tweet Queue"                                                                                                                  
  TRACKING_FILE      = "processed_urls.txt"                 
                                                                                                                                                      
  MAX_PER_FEED = 8                            
  MAX_TWEETS   = 8                                                                                                                                    
  MAX_REPLIES  = 10                                         
                                                                                                                                                      
  RSS_FEEDS = [                                             
      ("TechCrunch",   "https://techcrunch.com/feed/"),                                                                                               
      ("SaaStr",       "https://www.saastr.com/feed/"),     
      ("G2 Learn",     "https://learn.g2.com/rss.xml"),                                                                                               
      ("The Verge",    "https://www.theverge.com/rss/index.xml"),
      ("Entrepreneur", "https://www.entrepreneur.com/latest.rss"),                                                                                    
      ("Product Hunt", "https://www.producthunt.com/feed"),                                                                                           
      ("HackerNews",   "https://news.ycombinator.com/rss"),                                                                                           
  ]                                                                                                                                                   
                                                                                                                                                      
  REDDIT_TARGETS = [                                        
      ("entrepreneur",      "project management software"),                                                                                           
      ("entrepreneur",      "all in one tool recommend"),   
      ("smallbusiness",     "software recommendation"),                                                                                               
      ("smallbusiness",     "too many tools"),              
      ("smallbusiness",     "saas expensive"),                                                                                                        
      ("startups",          "saas tools team"),
      ("startups",          "project management"),                                                                                                    
      ("SaaS",              "alternative recommendation"),  
      ("projectmanagement", "software tool"),                                                                                                         
      ("productivity",      "tool recommendation team"),    
      ("digitalnomad",      "business software"),                                                                                                     
      ("Entrepreneur",      "expense management"),                                                                                                    
  ]                                           
                                                                                                                                                      
  # ── Prompts ───────────────────────────────────────────────────────────────────
                                                                                                                                                      
  FILTER_PROMPT = """You are a content strategist for Simplify Suite, an all-in-one business SaaS for small teams (1-25 people).
                                                                                                                                                      
  Review these news articles. Return ONLY the ones worth tweeting about.
                                                                                                                                                      
  RELEVANT: SaaS tools, business software, project management, team productivity, small business ops,
  expense/cashflow/budgeting, AI in business workflows, competitor news (monday.com, ClickUp, Asana,                                                  
  Notion, Rippling, Zoho, Freshworks, Trello, Odoo), SaaS pricing, consolidation, tool fatigue.                                                       
                                              
  NOT RELEVANT: consumer tech, gaming, hardware, pure politics, celebrity, sports.                                                                    
                                                                                                                                                      
  Return JSON only, no markdown:                                                                                                                      
  [{"index": 0, "reason": "why relevant"}]                                                                                                            
                                                                                                                                                      
  Nothing relevant? Return: []"""                           
                                                                                                                                                      
                                                                                                                                                      
  TWEET_PROMPT = """You are the social media manager for Simplify Suite (@SimplifySuite).
                                                                                                                                                      
  Simplify Suite: all-in-one business platform for small teams (1-25 people).                                                                         
  Replaces 5-10 tools: projects, budgets, cashflow, expenses, meetings, docs, performance reviews.                                                    
  Flat pricing. No enterprise bloat. Built by a startup for startups.                                                                                 
                                                            
  VOICE: Direct, sharp, slightly irreverent. Like a smart founder with honest takes.                                                                  
                                                                                                                                                      
  Write ONE tweet reacting to this article:                                                                                                           
  1. Interesting to SMB founders and ops managers                                                                                                     
  2. Angle: hot take / pain point / stat + opinion / contrast / soft product spotlight / question                                                     
  3. Feels like a real person wrote it                      
  4. Under 260 characters                                                                                                                             
  5. 1-2 hashtags max, only if natural                                                                                                                
  6. Occasionally (not always) ties back to Simplify Suite                                                                                            
                                                                                                                                                      
  DO NOT: start with Hey/Breaking/Exciting, use more than one exclamation mark,                                                                       
  use synergy/innovation/game-changing, be preachy, wrap tweet in quotes.                                                                             
                                                                                                                                                      
  Return ONLY the tweet text. Nothing else."""                                                                                                        
                                                                                                                                                      
                                                                                                                                                      
  REPLY_PROMPT = """You are the social media manager for Simplify Suite (@SimplifySuite).                                                             
                                                                                                                                                      
  Simplify Suite replaces 5-10 business tools (projects, budgets, cashflow, expenses, meetings,
  docs, performance reviews) with one flat-rate platform for small teams (1-25 people).                                                               
  Website: simplifysuite.io                                 
                                          
  Someone posted online asking for a tool or complaining about their setup.                                                                           
  Write a helpful reply that:                                                                                                                         
  1. Directly addresses their specific pain — reference what they actually said                                                                       
  2. Explains how Simplify solves exactly that problem (be specific, not generic)                                                                     
  3. Sounds helpful, not salesy                                                                                                                       
  4. Under 260 characters                                                                                                                             
  5. Ends with simplifysuite.io as a soft CTA                                                                                                         
  6. Do not start with I or We — lead with their problem or the solution                                                                              
  7. Max 1 hashtag                                                                                                                                    
                                                                                                                                                      
  Good examples:                                                                                                                                      
  "Running Asana + QuickBooks + Expensify as three separate tools is exactly what Simplify was built to fix. One platform, all connected.             
  simplifysuite.io"                                                                                                                                   
  "That gap between your project timeline and your actual budget is where money disappears. Simplify links them in real time. simplifysuite.io"       
                                                            
  Return ONLY the reply text. Nothing else."""                                                                                                        
   
                                                                                                                                                      
  # ── Groq ──────────────────────────────────────────────────────────────────────
                                                                                                                                                      
  def get_groq():                                                                                                                                     
      return Groq(api_key=GROQ_API_KEY)
                                                                                                                                                      
                                                            
  def call_groq(client, system_prompt, user_content, temperature=0.75, retries=3):
      for attempt in range(retries):
          try:                                                                                                                                        
              resp = client.chat.completions.create(
                  model="llama-3.3-70b-versatile",                                                                                                    
                  messages=[                                
                      {"role": "system", "content": system_prompt},
                      {"role": "user",   "content": user_content},                                                                                    
                  ],                          
                  temperature=temperature,                                                                                                            
                  max_tokens=350,                           
              )                                                                                                                                       
              return resp.choices[0].message.content.strip()
          except Exception as e:                                                                                                                      
              print(f"    Groq error (attempt {attempt+1}): {e}")
              if attempt < retries - 1:   
                  time.sleep(6)
      return None                                                                                                                                     
                                          
                                                                                                                                                      
  def clean_text(raw):                                                                                                                                
      if not raw:
          return None                                                                                                                                 
      t = raw.strip().strip('"').strip("'")                 
      for prefix in ["tweet:", "reply:", "text:"]:
          if t.lower().startswith(prefix):    
              t = t[len(prefix):].strip() 
      return t[:280] if 20 <= len(t) <= 300 else None                                                                                                 
                                                                                                                                                      
                                                                                                                                                      
  # ── Google Sheets ─────────────────────────────────────────────────────────────                                                                    
                                                                                                                                                      
  HEADERS = [                                                                                                                                         
      "#",                                                                                                                                            
      "Type",                                                                                                                                         
      "Tweet / Reply Text",                                 
      "Source",                               
      "Reply To URL",                     
      "Article / Post Title",
      "Generated At",                                                                                                                                 
      "Status",
      "Notes",                                                                                                                                        
  ]                                                         

  def get_worksheet():                                                                                                                                
      creds_dict = json.loads(SHEETS_CREDENTIALS)
      scopes     = ["https://www.googleapis.com/auth/spreadsheets"]                                                                                   
      creds      = Credentials.from_service_account_info(creds_dict, scopes=scopes)
      gc         = gspread.authorize(creds)   
      sheet      = gc.open_by_key(SHEET_ID)
                                                                                                                                                      
      try:                                                                                                                                            
          ws = sheet.worksheet(SHEET_TAB)                                                                                                             
      except gspread.WorksheetNotFound:                                                                                                               
          ws = sheet.add_worksheet(title=SHEET_TAB, rows=1000, cols=len(HEADERS))
          ws.append_row(HEADERS)              
          ws.format("A1:I1", {                                                                                                                        
              "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.18},
              "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},                                                     
              "horizontalAlignment": "CENTER",              
          })                                                                                                                                          
          print("  Created new sheet tab with headers")     
                                                                                                                                                      
      return ws                                             
                                                                                                                                                      
                                                                                                                                                      
  def get_next_serial(ws):                
      all_values = ws.get_all_values()                                                                                                                
      data_rows  = len(all_values) - 1                                                                                                                
      return max(data_rows + 1, 1)            
                                                                                                                                                      
                                                            
  def append_rows_to_sheet(ws, entries):                                                                                                              
      rows = []
      for e in entries:                                                                                                                               
          rows.append([                                     
              e["serial"],
              e["type"],                                                                                                                              
              e["tweet_text"],
              e["source"],                                                                                                                            
              e.get("reply_url", ""),                       
              e.get("post_title", ""),        
              e["generated_at"],          
              "pending",
              "",                                                                                                                                     
          ])
      if rows:                                                                                                                                        
          ws.append_rows(rows, value_input_option="USER_ENTERED")
          print(f"  Appended {len(rows)} rows to Google Sheet")
                                                                                                                                                      
                                              
  # ── Tracking ──────────────────────────────────────────────────────────────────                                                                    
                                                                                                                                                      
  def load_processed_urls():                                                                                                                          
      if not os.path.exists(TRACKING_FILE):                                                                                                           
          return set()                                                                                                                                
      with open(TRACKING_FILE, "r") as f:                   
          return set(line.strip() for line in f if line.strip())

                                                                                                                                                      
  def save_processed_urls(new_urls):
      with open(TRACKING_FILE, "a") as f:                                                                                                             
          for url in new_urls:                              
              f.write(url + "\n")         

                                                                                                                                                      
  # ── RSS Pipeline ──────────────────────────────────────────────────────────────
                                                                                                                                                      
  def fetch_rss_articles():                                                                                                                           
      articles = []
      for name, url in RSS_FEEDS:                                                                                                                     
          try:                                              
              feed  = feedparser.parse(url)
              count = 0                       
              for entry in feed.entries:  
                  if count >= MAX_PER_FEED:
                      break                                                                                                                           
                  title   = entry.get("title", "").strip()
                  link    = entry.get("link", "").strip()                                                                                             
                  summary = entry.get("summary", entry.get("description", ""))                                                                        
                  summary = re.sub(r"<[^>]+>", "", summary).strip()[:400]
                  if title and link:                                                                                                                  
                      articles.append({"title": title, "summary": summary, "url": link, "source": name})
                      count += 1                                                                                                                      
              print(f"  {name}: {count} articles")                                                                                                    
          except Exception as e:                                                                                                                      
              print(f"  {name}: failed - {e}")                                                                                                        
      return articles                                       
                                                                                                                                                      
                                              
  def filter_articles(client, articles):                                                                                                              
      if not articles:                                      
          return []                                                                                                                                   
      listing = "\n".join(
          f'{i}. "{a["title"]}" | {a["source"]} | {a["summary"][:180]}'                                                                               
          for i, a in enumerate(articles)                   
      )                                   
      raw = call_groq(client, FILTER_PROMPT, f"Articles:\n{listing}", temperature=0.2)
      if not raw:                                                                                                                                     
          return articles[:5]             
      try:                                                                                                                                            
          parsed  = json.loads(raw.replace("```json", "").replace("```", "").strip())                                                                 
          indices = [r["index"] for r in parsed if isinstance(r, dict) and "index" in r]
          result  = [articles[i] for i in indices if i < len(articles)]                                                                               
          print(f"  Relevant: {len(result)} of {len(articles)}")
          return result                                                                                                                               
      except Exception:                                     
          return articles[:5]                                                                                                                         
                                                            
                                                                                                                                                      
  # ── Reddit Pipeline ───────────────────────────────────────────────────────────                                                                    
  
  INTENT_KEYWORDS = [                                                                                                                                 
      "looking for", "recommend", "alternative", "replace", "switching from",
      "too expensive", "too many", "frustrated", "what do you use",
      "which tool", "best tool", "suggestion", "what software", "what app",                                                                           
      "anyone use", "comparison", "vs ", "need a tool", "need software",
      "help me find", "tried everything",                                                                                                             
  ]                                                         
                                                                                                                                                      
  def fetch_reddit_posts(processed_urls):
      posts   = []                                                                                                                                    
      seen    = set(processed_urls)                         
      headers = {"User-Agent": "SimplifySuiteBot/1.0"}
                                          
      for subreddit, keyword in REDDIT_TARGETS:
          try:                                                                                                                                        
              q   = urllib.parse.quote(keyword)
              url = (f"https://www.reddit.com/r/{subreddit}/search.json"                                                                              
                     f"?q={q}&restrict_sr=1&sort=new&limit=10&t=week")
              req = urllib.request.Request(url, headers=headers)
              with urllib.request.urlopen(req, timeout=10) as resp:                                                                                   
                  data = json.loads(resp.read())
                                                                                                                                                      
              for child in data.get("data", {}).get("children", []):                                                                                  
                  p        = child.get("data", {})
                  post_url = f"https://reddit.com{p.get('permalink', '')}"                                                                            
                  if post_url in seen:                      
                      continue
                  seen.add(post_url)                                                                                                                  
  
                  title = p.get("title", "").strip()                                                                                                  
                  body  = p.get("selftext", "").strip()[:500]
                  if not title:
                      continue                                                                                                                        
  
                  combined = (title + " " + body).lower()                                                                                             
                  if not any(kw in combined for kw in INTENT_KEYWORDS):
                      continue                
                                          
                  posts.append({
                      "title":     title,                                                                                                             
                      "body":      body,
                      "url":       post_url,                                                                                                          
                      "subreddit": subreddit,               
                      "score":     p.get("score", 0),
                  })                          
                                          
              time.sleep(1.2)
                                                                                                                                                      
          except Exception as e:
              print(f"  r/{subreddit} '{keyword}': {e}")                                                                                              
                                                            
      posts.sort(key=lambda x: x["score"], reverse=True)
      unique = list({p["url"]: p for p in posts}.values())[:MAX_REPLIES]
      print(f"  Found {len(unique)} relevant Reddit posts")
      return unique                                                                                                                                   
  
                                                                                                                                                      
  # ── Main ──────────────────────────────────────────────────────────────────────

  def main():                                                                                                                                         
      for var, name in [(GROQ_API_KEY, "GROQ_API_KEY"),
                        (SHEETS_CREDENTIALS, "GOOGLE_SHEETS_CREDENTIALS"),                                                                            
                        (SHEET_ID, "GOOGLE_SHEET_ID")]:     
          if not var:                     
              raise RuntimeError(f"{name} environment variable not set")
                                                                                                                                                      
      print("=" * 60)                         
      print(f"Simplify Suite Tweet Generator - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")                                                   
      print("=" * 60)                                       
                                                                                                                                                      
      groq_client    = get_groq()
      processed_urls = load_processed_urls()                                                                                                          
      new_entries    = []                                   
      new_urls       = []                 
      now            = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                                                                                                                                                      
      print("\nConnecting to Google Sheets...")
      ws     = get_worksheet()                                                                                                                        
      serial = get_next_serial(ws)                          
      print(f"  Starting at serial #{serial}")                                                                                                        
   
      # ── 1. RSS -> Original Tweets ─────────────────────────────────────────────                                                                    
      print("\n[1/2] RSS News -> Original Tweets")          
      articles = fetch_rss_articles()
      fresh    = [a for a in articles if a["url"] not in processed_urls]                                                                              
      print(f"  New: {len(fresh)} (skipped {len(articles)-len(fresh)} already seen)")
                                                                                                                                                      
      if fresh:                                             
          relevant = filter_articles(groq_client, fresh)[:MAX_TWEETS]
          print(f"  Generating {len(relevant)} tweets...")                                                                                            
          for i, article in enumerate(relevant, 1):
              print(f"    [{i}/{len(relevant)}] {article['title'][:55]}...")                                                                          
              text = clean_text(call_groq(                  
                  groq_client, TWEET_PROMPT,                                                                                                          
                  f"Title: {article['title']}\nSource: {article['source']}\nSummary: {article['summary']}"
              ))                                                                                                                                      
              if text:                                      
                  new_entries.append({                                                                                                                
                      "serial":       serial,
                      "type":         "Original",                                                                                                     
                      "tweet_text":   text,                 
                      "source":       article["source"],
                      "reply_url":    "",                                                                                                             
                      "post_title":   article["title"],
                      "generated_at": now,                                                                                                            
                  })                                        
                  new_urls.append(article["url"])
                  print(f"      -> {text[:75]}...")
                  serial += 1                                                                                                                         
              time.sleep(1)
                                                                                                                                                      
      # ── 2. Reddit -> Reply Drafts ─────────────────────────────────────────────
      print("\n[2/2] Reddit -> Reply Drafts")
      reddit_posts = fetch_reddit_posts(processed_urls)
                                                                                                                                                      
      if reddit_posts:
          print(f"  Generating {len(reddit_posts)} replies...")                                                                                       
          for i, post in enumerate(reddit_posts, 1):        
              print(f"    [{i}/{len(reddit_posts)}] r/{post['subreddit']}: {post['title'][:50]}...")
              text = clean_text(call_groq(
                  groq_client, REPLY_PROMPT,                                                                                                          
                  f"Subreddit: r/{post['subreddit']}\nTitle: {post['title']}\nBody: {post['body']}"
              ))                                                                                                                                      
              if text:                                                                                                                                
                  new_entries.append({
                      "serial":       serial,                                                                                                         
                      "type":         "Reddit Reply",       
                      "tweet_text":   text,
                      "source":       f"r/{post['subreddit']}",                                                                                       
                      "reply_url":    post["url"],
                      "post_title":   post["title"],                                                                                                  
                      "generated_at": now,                  
                  })
                  new_urls.append(post["url"])                                                                                                        
                  print(f"      -> {text[:75]}...")
                  serial += 1                                                                                                                         
              time.sleep(1)                                 
                                          
      # ── Save ──────────────────────────────────────────────────────────────────
      print(f"\nTotal generated: {len(new_entries)}")                                                                                                 
      if new_entries:                         
          append_rows_to_sheet(ws, new_entries)                                                                                                       
          save_processed_urls(new_urls)                     
      else:                                                                                                                                           
          print("Nothing new this run.")
                                                                                                                                                      
      print("Done.")                                        

                                              
  if __name__ == "__main__":              
      main()
