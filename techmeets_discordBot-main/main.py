# coding: UTF-8

import discord
import gspread
import datetime
import pytz

from oauth2client.service_account import ServiceAccountCredentials

import os

from dotenv import load_dotenv
load_dotenv()


""""
client object:
    サーバへの接続情報

DS_TOKEN str:
    DiscordBotのAPIトークン

SP_TOKEN str:
    共有設定をしているSpredsheetのトークン


scopes list:
    APIの権限

main_channel int:
    メインチャンネルのID

submit_text_channel int:
    講師陣用のチャンネルのID

primer_list list:
    プライマー用のテキストチャンネルのID

trybee_list list:
    トライビー用のテキストチャンネルのID

teacher_id str:
    講師陣のメンションID
"""

client = discord.Client()  # 接続に必要なオブジェクトを生成

DS_TOKEN = os.getenv('DS_TOKEN')
SP_TOKEN = os.getenv('SP_TOKEN')

online_times = []

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/spreadsheets']


main_channel = 576992785324965890
submit_text_channel = 658613626986430464

matter_category = 642256853044035594

primer_list = [577004424761704449, 586718546860441600, 589444108360220732,
               632079629116768266, 589450019917004800, 626969460099645461, 624459175996686337]
trybee_list = [695256695093592105,
               696971058103975976, 696970944568229888]
teacher_id = "577000224585809930"


primer_dict = trybee_dict = ''


def get_sheet():
    """
    グーグルスプレッドシートの情報を取得

    Returns
    -------
    sheet1 : object
        シート1のオブジェクト

    sheet2 : object
        シート2のオブジェクト
    """
    global sheet2
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'TechmeetsBot-2efec20f47d0.json', scope)  # APIで取得したクレデンシャルファイルを読み込み
    gc = gspread.authorize(credentials)  # OAuth2の資格情報を使用してGoogle APIにログイン
    worksheet = gc.open_by_key(SP_TOKEN)  # 共有設定したスプレッドシートのシート1を取得
    allsheet = worksheet.worksheets()  # シートの一覧が取得
    for sheet in allsheet:  # シートそれぞれのオブジェクトを取得
        if sheet.title == "シート2":
            sheet2 = sheet
        elif sheet.title == "シート1":
            sheet1 = worksheet.sheet1
    return sheet1, sheet2


def set_online_time(name, now_time):
    """
    オンラインになった時の時間をセット

    Params
    -------
    name : str
        ユーザ名
    now_time : datetime
        現在の時間を取得
    """
    global online_times
    user_time = {"name": name, "time": now_time}
    online_times.append(user_time)


def get_state_time(name, now_time):
    """
    滞在時間を取得

    Params
    -------
    name : str
        ユーザ名
    now_time : datetime
        現在の時間を取得

    Returns
    -------
    set_time : datetime
        滞在時間
    """
    global online_times
    for index, i in enumerate(online_times):  # ToDo: Forを使わないやり方で
        if name == i["name"]:
            online_times.pop(index)
            set_time = now_time - i["time"]
            return set_time

# @client.event
# async def on_member_update(before,after):
#    """
#     ユーザがオンラインになった時に発火するイベント

#     Params
#     -------
#     before : object
#         オンライン時
#     after : object
#         オフライン時
#    """
#   now_time = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
#   yobi = ["月","火","水","木","金","土","日"]
#   worksheet, sheet2 = get_sheet()
# # ステータスチェック
#   if (before.status != after.status) and (after.status == discord.Status.online):
#     set_online_time(after.name, now_time)
#   elif (before.status != after.status) and (after.status == discord.Status.offline):
#     state_time = get_state_time(after.name, now_time)
#     if state_time is not None:
#       values1 = sheet2.get_all_values()
#       vertical = len(values1) + 1
#       weekday = now_time.weekday()
#       sheet2.update_cell(vertical, 1, str(state_time))
#       sheet2.update_cell(vertical, 2, after.name)
#       sheet2.update_cell(vertical, 3, yobi[weekday])
#       sheet2.update_cell(vertical, 4, str(now_time))
#       sheet2.update_cell(vertical, 5, str(after.roles))


async def delete_message(message):
    """
    メッセージの削除

    Params
    -------
    message : object
        メッセージオブジェクト
    """
    channel = client.get_channel(int(message.channel.id))  # メッセージチャンネルの取得
    msg = await channel.fetch_message(int(message.id))  # メッセージの取得
    await msg.delete()  # メッセージの削除


def get_dict_channel(id_list):
    """
    チャンネルの取得

    Params
    -------
    id_list : list
        取得したいチャンネルのIDのリスト
    """
    dict_channel = {}
    for index, channnel_id in enumerate(id_list):
        dict_channel[index] = client.get_channel(channnel_id)
    return dict_channel


@client.event
async def on_message(message):
    """
    メッセージを受け取った時に発火するイベント

    Params
    -------
    message : object
        メッセージオブジェクト
    """
    if message.author != client.user:
        role_name = [role.name for role in message.author.roles]
        # 講師、サポータが！をつけている時のみ
        if ('講師' in role_name or 'サポーター' in role_name) and True == message.content.startswith('!'):
            await delete_message(message)  # メッセージの削除
            await command_text_submit(message)  # コマンドメッセージの送信
        # 質問ちゃんねるのカテゴリの場合
        if message.channel.category_id != main_channel or message.channel.category_id != matter_category:
            if client.user in message.mentions:
                alert_teacher_channnel(message)  # 講師陣が見れるテキストチャンネルに送信
                replay_text(message)  # 一次対応テキストの送信


async def alert_teacher_channnel(message):
    """
    講師陣向けテキストチャンネルに送信

    Params
    -------
    message : object
        メッセージオブジェクト
    """
    submit_channel = client.get_channel(submit_text_channel)
    channel_name = message.channel
    message_content = message.content.split('>')[-1]
    send_text = f'<@&{teacher_id}>\n{message.channel.mention}から以下の質問きました\n```\n{message_content}\n```'
    await submit_channel.send(send_text)


async def replay_text(message):
    """
    一次対応テキストの送信

    Params
    -------
    message : object
        メッセージオブジェクト
    """
    reply = f'{message.author.mention}```md\n質問ありがとうございます！！！\n講師の方に連絡させていただきます。\n```'
    await message.channel.send(reply)


def append_spredsheet(channel_name, message_content):
    """
    スプレッドシートに質問を追加

    Params
    -------
    channel_name : str
        チャンネルの名前

    message_content : str
        メッセージの内容
    """
    worksheet, sheet2 = get_sheet()
    values1 = worksheet.get_all_values()
    vertical = len(values1) + 1
    worksheet.update_cell(vertical, 1, vertical)
    worksheet.update_cell(vertical, 2, str(channel_name))
    worksheet.update_cell(vertical, 3, str(
        datetime.datetime.now(pytz.timezone('Asia/Tokyo'))))
    worksheet.update_cell(vertical, 4, message_content)


# def create_text_channel(message):
# if True ==  message.content.startswith('/mkch'):
#   print('bot action!')
#   msg = message.content
#   ch_name = msg.split('/mkch')[1]
#   print(ch_name)
#   category_id = 655032505770049566
#   category = message.guild.get_channel(category_id)
#   new_channel = await category.create_text_channel(name=ch_name)
#   print(new_channel)
#   reply = f'{new_channel.mention} を作成しました'
#   await message.channel.send(reply)
# elif 'コマンド' in message.content:
#   command_list = '/mkch:チャンネルを作成する。\n例:/mkch999_user'
#   await message.channel.send(command_list)


async def command_text_submit(message):
    """
    典型文を追加

    Params
    -------
    message : object
        メッセージオブジェクト
    """
    student_name_channel = message.channel.name
    student_name = student_name_channel.split("_")[1]
    if True == message.content.startswith('!copy'):
        # await delete_message(message)
        copy_message = "過去案件の模写課題はこちらになります\n\n要件定義：\nhttps://docs.google.com/document/d/1-NHH5EyROcPbVX212j81LJZmMgzEwdbMCw7Ec5qYYTA/edit?usp=sharing \nこういった案件のもので、\nデザインカンプ：\nhttps://drive.google.com/drive/folders/1cMX1Kq_UBcZtelbYdWAhFURZVx1eWqZn?usp=sharing \n\nこちらの中のPDFを模写してコーディング頂けますと幸いです！画像はご自身のものかフリー画像を使っていただければと思います。\n左側がPC版、右側がスマホ版となっております。"
        await message.channel.send(copy_message)
    elif True == message.content.startswith('!study'):
        study_text = f"今後の流れに関しては{student_name}さんの学びたい内容に’添わせて進めて行きたいと講師一同考えております。\n今で興味があるものや言語、作りたい制作物、受けたい資格、などはございますでしょうか:thinking:\nまた並行して講義動画もどんどんみて課題があればやっていただけると知識もついていきますのでよろしくおねがいします！"
        await message.channel.send(study_text)
    elif True == message.content.startswith('!start'):
        start_text = f"{student_name}さん、こんにちは！techmeetsです。\n今月から宜しくお願いいたします。\n\nさて、techmeetsではオムニバス形式の学習に加えて、個々人と時間を作って目標を設定し課題をこなしていくカリキュラムがございます。\n目標設定のヒアリング面談を行うため、\n明日以降、一週間程度を目安に都合の付く時間をこちらのチャットでお答えください。返信を頂いたのち、担当の講師から改めてご連絡差し上げます。\ndiscordを使ったオンラインでのボイスチャットを予定していますので、お時間ありましたら__マイク等のデバイスの設定__をして頂ければなお助かります。\n\n（面談に際して、__**「エンジニアリングを学び、将来どうなりたいか」「6ヶ月後、どうなりたいか」**__などを明確にして頂けるとスムーズかと思います！）\n\n\nまた、日程調整の間に事前にお教えいただきたいプロフィールがございます。\n●お名前（フリガナ必須）\n●生年月日\n●現住所\n●電話番号\n\n以上となります、よろしくお願いいたします。"
        await message.channel.send(start_text)
    elif True == message.content.startswith('!ftp'):
        ftp_text = "これだけだと判断し兼ねますので、サーバにアップしていただけると幸いです。アップ方法に関しては、サーバ第二回が参考になります。同時にURLも教えていただけると助かります。\nhttps://techmeets.jp/student/3桁の受講生番号+名前/転送したhtmlファイル名 \n[ https://techmeets.jp/student/111_tanaka/test.html ]\n↑111番田中さんがtest.htmlを送った場合"
        await message.channel.send(ftp_text)
    elif True == message.content.startswith('!site'):
        port_text = "①Name\nまず名前に加えてアイコン、そこにtwitter, facebook, Qiita, githubのアイコンも追加。\n\n②Skills\n自分が何をどのくらいできるのか、\nちょっとできるのような表現ではなく定量的や〜〜ができると行った分かりやすいもの。\n\n③Experience（なければ①を詳しく書きます）\n自分の経歴ですね、どこで何年何やったかです。\n\n④Writing\n実際に作ったものや、書いた本など成果物ベースで載せます。\n\n\n１〜４でポートフォリオに必要な情報は集まると思います\nこれを軸に他の制作物にとりかかるといいと思います。"
        await message.channel.send(port_text)
    elif True == message.content.startswith('!private'):
        private_text = "ファイル名ではなく、公開鍵の中身のテキストやファイルをDiscordにアップロードをしていただけると幸いです。"
        await message.channel.send(private_text)
    elif True == message.content.startswith('!primer'):
        primer_text = f"{student_name}さん、こんにちは！techmeets primerです。\n"\
            "今月から宜しくお願いいたします。\n"\
            "さて、改めてtechmeets primerのご利用できるチャンネルを簡単にご説明させていただきます。\n\n"\
            "{primer_dict[0].mention} \n皆さまからいただいた質問のうち、多く寄せられたものがFAQ方式で追加されていきます。"\
            "\n\n{primer_dict[1].mention} \n講義の配信情報がこちらに載せられていきます。"\
            "\n毎週水・土曜に更新されます。\n\n{primer_dict[2].mention} \n講師陣のオススメ記事や時事ネタなどを発信していきます。"\
            "\n\n{primer_dict[3].mention}\n生徒さん自身が学習の途中で参考になった記事であったり参考文献を共有できるようなスペースになっています。"\
            "\n\n{primer_dict[4].mention} \ntechmeets primerにおけるモクモク会の時にご利用下さい。"\
            "\n\n{primer_dict[5].mention} \n今後の講義の日程が載せられています。"\
            "\n\n{primer_dict[6].mention} \nまずはここからtechmeets primerの学習を始めていきましょう。"\
            "\nエンジニアとしての基礎が詰まっています。\n\n※尚、本チャットで講師への質問対応はしておりません"\
            "\nもくもく会に参加していただいた際のチャットでは回答致します！"\
            "\n\n※案件の案内及び、面談に関してはprimerのサービスに含まれておりませんのであらかじめご了承ください。"\
            "\n\nでは３ヶ月共に頑張りましょう！！\n"\
            "上記の事に関して簡単に説明させていただければと思いますので、５〜１０分程お話できるタイミングございましたらいくつか日程いただければこちらで調整させていただきます！"
        await message.channel.send(primer_text)
    elif True == message.content.startswith('!finish'):
        finish_text = f"{student_name}さん、6ヶ月間techmeetsを受講いただきありがとうございました。\n\n"\
            "本日をもちまして、サービスの方を終了させていただきます。\n\n"\
            "今後ですが、テックミーツのコンテンツを確認及びご利用することができなくなります。\n\n"\
            "質問は対応できなくなりますが、TRYBEEやTechmeets継続プランを検討する場合には、"\
            "このテキストチャンネル内で連絡することができますので、もしご連絡等がございましたら、ご連絡ください。\n\n"\
            "どうぞよろしくお願いいたします。"
        await message.channel.send(finish_text)
    elif True == message.content.startswith('!git'):
        git_text = "アカウント名の方ありがとうございます。登録させていただきました。\n"\
            "確認メールが届いていると思うので確認のほどよろしくお願いいたします。"
        await message.channel.send(git_text)
    elif True == message.content.startswith('!pre_finish'):
        pre_finish_text = "※このメッセージは今月末で受講期間が終了する方に向けて送信しています。\n"\
            "万が一受講期間がずれていた場合はご連絡いただけると幸いです。\n\n"\
            "【{student_name}】さん、平素よりTechmeetsをご利用いただきありがとうございます。\n\n"\
            "受講期間が残すところ1週間となりましたことをご連絡致します。\n\n"\
            "本サービスは月末まで利用可能です。\n"\
            "月末の翌営業日(月初め)に受講終了通知とともにサービスがご利用できなくなりますのでご承知おきください。\n\n"\
            "また、お手数をおかけしますが、今後私たちのサービス改善のために下記リンクからアンケートのご協力をお願いします。\n"\
            "https://docs.google.com/forms/d/e/1FAIpQLSexFfZeT7pAiHOeAnTwfQgYcEJ0fptb2onypo5S5v0URzjJmQ/viewform?usp=sf_link\n\n"\
            "それでは残りの受講期間もどうぞよろしくお願い申し上げます。\n".format(
                student_name=student_name)
        await message.channel.send(pre_finish_text)
    elif True == message.content.startswith('!trybee'):
        trybee_text = f'{student_name}さん、TRYBEEへご入会いただきありがとうございます。\n\n各種チャンネルについての説明は、{trybee_dict[0].mention}に をご覧ください。\n\nご確認いただけましたら、まずは{trybee_dict[1].mention} チャンネルでご自身をアピールしてください！\nそちらにすべて載せていただいても大丈夫ですし、ご挨拶は{trybee_dict[2].mention}で行っていただいてもOKです。\n\nその後、TRYBEEに参加していただいた皆さんに、前提のスキルとして身に着けておいて欲しいものを以下に纏めてあります。\nhttp://u0u0.net/hKwV\n\nまずはこちらを参考にして、掲示板やログイン処理を行えるwebページや、\n各種簡単なツール開発等を熟せるようになっていただければと思います。\n\nまた、以上のコンテンツとは別に、こちらの個人チャットもございますが、\nこちらは我々から直接皆さんと案件に関するやり取りを行うためのチャンネルになっております。\nそのため、通知漏れなど無いようにしていただければ幸いです。\n\nそれでは今後ともよろしくお願いいたします！'
        await message.channel.send(trybee_text)
    elif True == message.content.startswith('!anketo'):
        anketo_text = f'{student_name}さん/n以前はtechmeetsをご利用いただきまして誠にありがとうございました。/nその後いかがお過ごしでしょうか。/n/n techmeetsでは卒業生を対象にフォローアップアンケートを実施しております。/n差し支えの無い範囲で構いませんので、回答のご協力を何卒よろしくお願い申し上げます。/n https://forms.gle/KL4vX9fvGYkXpSVy9 /n/nお忙しい中お読みいただきまして誠にありがとうございます。/n皆様の今後のご活躍をお祈り申し上げます。さん、TRYBEEへご入会いただきありがとうございます。\n\n各種チャンネルについての説明は、{trybee_dict[0].mention}に をご覧ください。\n\nご確認いただけましたら、まずは{trybee_dict[1].mention} チャンネルでご自身をアピールしてください！\nそちらにすべて載せていただいても大丈夫ですし、ご挨拶は{trybee_dict[2].mention}で行っていただいてもOKです。\n\nその後、TRYBEEに参加していただいた皆さんに、前提のスキルとして身に着けておいて欲しいものを以下に纏めてあります。\nhttp://u0u0.net/hKwV\n\nまずはこちらを参考にして、掲示板やログイン処理を行えるwebページや、\n各種簡単なツール開発等を熟せるようになっていただければと思います。\n\nまた、以上のコンテンツとは別に、こちらの個人チャットもございますが、\nこちらは我々から直接皆さんと案件に関するやり取りを行うためのチャンネルになっております。\nそのため、通知漏れなど無いようにしていただければ幸いです。\n\nそれでは今後ともよろしくお願いいたします！'
        await message.channel.send(anketo_text)
    elif True == message.content.startswith('!comand'):
        comands = "模写課題: !copy\n今後の流れ: !study\n開始文: !start\nftp文: !ftp\nポートフォリオ: !site"
        await message.channel.send(comands)


if __name__ == '__main__':
    primer_dict = get_dict_channel(primer_list)  # チャンネルを辞書型として保持
    trybee_dict = get_dict_channel(trybee_list)  # チャンネルを辞書型として保持
    # Botの起動とDiscordサーバーへの接続
    client.run(DS_TOKEN)
