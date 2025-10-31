import jieba
from wordcloud import WordCloud
import matplotlib.pyplot as plt
# define the function
def generate_wordcloud():
    with open('data/youtube/Honkai.json', "r", encoding="utf-8") as f: # the name according to your setting-see youtube_catch_main
        comments = json.load(f)

    texts = [item["text"] for item in comments]
    print(f"have loaded {len(texts)} comments")
    all_text = " ".join(texts)
    texts_for_wordcloud = all_text.lower()
    #word cloud setting and generate
    stop_words = set(['and', 'the', 'to', 'a', 'in','be','but','she','he','we','with','this','would','ever','that','i'])
    wc = WordCloud(
        font_path="msyh.ttc",  # 微软雅黑字体路径（显示中文）
        width=1000,
        height=600,
        background_color="white",
        stopwords=stop_words
    )

    # 生成词云
    wc.generate(texts_for_wordcloud)

    # 显示词云
    plt.figure(figsize=(10, 6))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis("off")
    plt.title("YouTube 评论词云", fontsize=16)
    plt.show()