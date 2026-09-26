#include "HUD/SoraHUDPanels.h"
#include "ArenaKernelSubsystem.h"
#include "ArenaWalletSubsystem.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPracticeDirector.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Internationalization/Text.h"

// The title and pause menu: story or practice status, class choice, controls,
// the wallet and transaction panels, and the New Campaign confirmation.
void SoraHUDPanels::DrawMenu(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,H=Frame.H,S=Frame.S,JapaneseSubtitleScale=Frame.JapaneseSubtitleScale,EnglishSubtitleScale=Frame.EnglishSubtitleScale,JapaneseSubtitleLineHeight=Frame.JapaneseSubtitleLineHeight,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    const UArenaWalletSubsystem* MenuWallet=HUD.GetWorld()->GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>();
    const bool bCompactClasses=MenuWallet&&MenuWallet->bHasUnverifiedJoinPreview;
    UTexture2D* TitleArt=HUD.TitleArt();
    if(TitleArt)
    {
        const float AreaH=H-75*S,ImageAspect=static_cast<float>(TitleArt->GetSizeX())/FMath::Max(1,TitleArt->GetSizeY());
        const float Aspect=W/FMath::Max(1.f,AreaH);
        const float USize=FMath::Min(1.f,Aspect/ImageAspect),VSize=FMath::Min(1.f,ImageAspect/Aspect);
        HUD.DrawTexture(TitleArt,0,75*S,W,AreaH,(1-USize)*.5f,(1-VSize)*.5f,USize,VSize,FLinearColor(1,1,1,.8f));
    }
    HUD.Panel(0,75*S,W,H,FLinearColor(.013,.027,.033,TitleArt?.58f:.9f));
    HUD.Panel(40*S,95*S,1190*S,700*S,FLinearColor(.013,.027,.033,.45f));
    const float L=80*S;
    HUD.Label(TEXT("剣を、工房を、民の手に。"),L,112*S,.55*S,Gold);
    HUD.Label(NSLOCTEXT("SoraArena", "MenuTitle", "猫柳生").ToString(),L,155*S,2.1*S,Ivory);
    HUD.Label(TEXT("ニャーギュウ ― 異星の債務帝国に挑む、侍猫の物語。"),L,257*S,.65*S,Muted);
    FString MenuChapter = TEXT("稽古場");
    FString MenuChapterEnglish = TEXT("Training ground");
    if(G->bDeterministicPractice) { MenuChapter=TEXT("武芸稽古 / オフライン"); MenuChapterEnglish=TEXT("Offline practice"); }
    else if(G->Campaign()->bCampaignComplete&&G->bCampaign) { MenuChapter=TEXT("猫柳生、解放済み"); MenuChapterEnglish=TEXT("Nyaagyu liberated"); }
    else if(G->bCampaign)
    {
        MenuChapter=FString::Printf(TEXT("第 %02d 章  /  %s"),G->Campaign()->ChapterId+1,*FSoraCatalog::Get().Chapter(G->Campaign()->ChapterId).Title);
        MenuChapterEnglish=FString::Printf(TEXT("Chapter %d: %s"),G->Campaign()->ChapterId+1,*FSoraCatalog::Get().Chapter(G->Campaign()->ChapterId).TitleEnglish);
    }
    HUD.Label(G->bEnglishSubtitles?MenuChapter+TEXT("   ")+MenuChapterEnglish:MenuChapter,L,300*S,.8*S,Teal);
    const int32 DisplayClass=G->bCampaign?0:G->SelectedClass;
    const FSoraMap& MenuMap=FSoraCatalog::Get().Map(G->MapId);
    const FSoraClass& MenuClass=FSoraCatalog::Get().Class(DisplayClass);
    HUD.Label(G->bEnglishSubtitles
        ?FString::Printf(TEXT("%s  |  %s   /   %s  |  %s"),*MenuMap.Name,*MenuClass.Role,*MenuMap.NameEnglish,*MenuClass.RoleEnglish)
        :FString::Printf(TEXT("%s  |  %s"),*MenuMap.Name,*MenuClass.Role),L,340*S,.6*S,Ivory);
    HUD.Label(G->Campaign()->bCampaignComplete&&G->bCampaign?TEXT("物語は完結した。N はじめから   P 武芸稽古   M マップ変更"):TEXT("ENTER 続ける   B 保存した物語へ   N はじめから   P 武芸稽古   M マップ変更"),L,397*S,.52*S,Ivory);
    HUD.Label(TEXT("パッド：A 続ける   View 保存した物語へ   Y はじめから   X 武芸稽古   十字上 マップ   LB / RB 流儀   Start メニュー"),L,425*S,.42*S,Muted);
    if(G->bCampaign)
    {
        HUD.Label(TEXT("主人公  /  ニャーコト"),L,465*S,.65*S,Gold);
        HUD.Label(TEXT("猫柳生新陰流の剣を学び、生産を奪われた民とともに戦う。"),L,518*S,.55*S,Ivory);
        if(G->bEnglishSubtitles) HUD.Label(TEXT("Nyaakoto fights beside the people who restore production."),L,554*S,EnglishSubtitleScale,Muted);
        HUD.Label(TEXT("六つの対戦流儀は P 武芸稽古で試せます。"),L,610*S,.46*S,Teal);
    }
    else
    {
        HUD.Label(TEXT("流儀を選ぶ  /  変更すると、この戦いをやり直します"),L,465*S,.55*S,Gold);
        for(int32 I=0;I<6;++I)
        {
            const float X=L+(I%(bCompactClasses?2:3))*385*S;
            const float Y=(bCompactClasses?500+(I/2)*57:515+(I/3)*84)*S;
            HUD.Panel(X-10*S,Y-8*S,355*S,(bCompactClasses?53:69)*S,I==G->SelectedClass?FLinearColor(.08,.25,.26,.9):FLinearColor(.07,.095,.11,.9));
            HUD.Label(G->bEnglishSubtitles
                ?FString::Printf(TEXT("F%d   %s   %s"),I+1,*FSoraCatalog::Get().Class(I).Name,*FSoraCatalog::Get().Class(I).NameEnglish)
                :FString::Printf(TEXT("F%d   %s"),I+1,*FSoraCatalog::Get().Class(I).Name),X,Y,.68*S,I==G->SelectedClass?Teal:Ivory);
            HUD.Label(FSoraCatalog::Get().Class(I).Role,X,Y+28*S,.42*S,Muted);
        }
    }
    if(G->bDeterministicPractice)
    {
        // The weapon the kernel seats the player with: the admitted special,
        // else the class's ranged weapon, or its blade in Melee only.
        const FSoraPracticeConfig& Config=G->Practice()->Config;
        const FSoraWeapon& Weapon=FSoraCatalog::Get().Weapon(SoraPractice::EntryWeapon(Config.Mode,G->SelectedClass,Config.SpecialWeaponId));
        HUD.Label(TEXT("入場時の武器： ")+Weapon.Name+TEXT("  /  メニューで 1 標準装備、3 特殊武器"),L,680*S,.46*S,Gold);
        HUD.Label(TEXT("WASD 移動   マウス 照準   左クリック 射撃   右クリック 近接   R 装填   Ctrl 防御   Q 技   Space 跳躍   Tab 戦況表"),L,725*S,.50*S,Ivory);
        HUD.Label(TEXT("倒れている間に 1・2・3 で次の武器、Q・E で流儀を選べます。Esc メニュー / F10 英語字幕。XOR は預けません。"),L,763*S,.45*S,Ivory);
        if(G->bEnglishSubtitles)
            HUD.Label(FString::Printf(TEXT("Enters with %s (1 standard, 3 special). While down, 1/2/3 pick the next weapon and Q/E the class. Tab: scoreboard. No XOR is bonded."),*Weapon.NameEnglish),
                L,787*S,.43*S,Muted);
        if(auto* K=G->Kernel()) if(!K->PracticeError.IsEmpty()) HUD.WrappedLabel(K->PracticeError,L,447*S,.4*S,Gold,W-L*2,20*S,1);
    }
    else
    {
        HUD.Label(TEXT("WASD 移動   マウス 照準   左クリック 射撃   右クリック 斬撃   Ctrl 防御   Shift 疾走   Space 跳躍"),L,725*S,.49*S,Ivory);
        HUD.Label(G->bCampaign&&G->Campaign()->ChapterId>0?
            TEXT("1 銃   2 刀   3 特殊   4 和弓   5 槍   6 薙刀   R 装填   E 調べる   F10 英語字幕"):
            TEXT("1 主武器   2 近接武器   3 特殊武器の試用   R 装填   E 調べる   Esc メニュー   F10 英語字幕"),L,763*S,.55*S,Ivory);
        if(G->bCampaign&&G->Campaign()->ChapterId>0&&G->bEnglishSubtitles)
            HUD.Label(TEXT("Campaign: 4 yumi, 5 yari, 6 naginata. Hold and release to draw the yumi."),L,787*S,.43*S,Muted);
    }
    HUD.Label(TEXT("IROHA CONNECT  /  C 接続を開始   L ウォレットを開く   X 接続を解除"),L,815*S,.52*S,Gold);
    if(const UArenaWalletSubsystem* Wallet=MenuWallet)
    {
        HUD.WrappedLabel(Wallet->StatusText,L,852*S,.46*S,Muted,W-L*2,23*S,2);
        if(!Wallet->ApprovedAccount.IsEmpty()) HUD.Label(TEXT("承認済み： ")+Wallet->ApprovedAccount.Left(62),L,902*S,.42*S,Teal);
        if(Wallet->TransactionState!=EArenaTransactionState::None&&Wallet->State!=EArenaWalletState::AwaitingApproval)
        {
            const float TxX=W-700*S,TxY=270*S,TxW=650*S;
            HUD.Panel(TxX,TxY,TxW,170*S,FLinearColor(.013,.027,.033,.94f));
            HUD.Label(TEXT("署名・台帳の状態"),TxX+20*S,TxY+12*S,JapaneseSubtitleScale,Gold);
            HUD.WrappedLabel(Wallet->TransactionStatusText,TxX+20*S,TxY+45*S,JapaneseSubtitleScale,Ivory,TxW-40*S,JapaneseSubtitleLineHeight,2);
            if(G->bEnglishSubtitles)
            {
                const TCHAR* EnglishState=TEXT("Transaction status unavailable.");
                switch(Wallet->TransactionState)
                {
                case EArenaTransactionState::AwaitingSignature: EnglishState=TEXT("Awaiting signature; check terms and fees."); break;
                case EArenaTransactionState::Signed: EnglishState=TEXT("Signed locally; not submitted."); break;
                case EArenaTransactionState::Submitting: EnglishState=TEXT("Submitting to the isolated test network."); break;
                case EArenaTransactionState::Pending: EnglishState=TEXT("Waiting for on-chain finality."); break;
                case EArenaTransactionState::Uncertain: EnglishState=TEXT("Status unknown; do not resend."); break;
                case EArenaTransactionState::Finalized: EnglishState=TEXT("Torii reports applied; match entry is separate."); break;
                case EArenaTransactionState::Rejected: EnglishState=TEXT("Rejected or expired on-chain."); break;
                case EArenaTransactionState::Cancelled: EnglishState=TEXT("Cancelled before submission."); break;
                case EArenaTransactionState::None: break;
                }
                HUD.Label(EnglishState,TxX+20*S,TxY+118*S,EnglishSubtitleScale,Muted);
            }
        }
        if(Wallet->bHasUnverifiedJoinPreview)
        {
            const float PreviewX=W-700*S,PreviewY=455*S,PreviewW=650*S;
            HUD.Panel(PreviewX,PreviewY,PreviewW,540*S,FLinearColor(.013,.027,.033,.96f));
            HUD.Label(TEXT("参加条件の下書き  /  未検証"),PreviewX+20*S,PreviewY+12*S,.68*S,Gold);
            if(G->bEnglishSubtitles) HUD.Label(TEXT("UNVERIFIED Join scaffold; no wallet approval."),PreviewX+20*S,PreviewY+43*S,.42*S,Muted);
            HUD.Label(TEXT("申請入金額: ")+Wallet->JoinPreviewStake,PreviewX+20*S,PreviewY+78*S,.44*S,Ivory);
            HUD.WrappedLabel(TEXT("資産 ID（申請）: ")+Wallet->JoinPreviewAsset,PreviewX+20*S,PreviewY+110*S,.38*S,Muted,PreviewW-40*S,18*S,2);
            HUD.WrappedLabel(TEXT("NFT 装備予約（申請）: ")+Wallet->JoinPreviewNftReservations,PreviewX+20*S,PreviewY+152*S,.38*S,Ivory,PreviewW-40*S,18*S,2);
            if(!Wallet->JoinPreviewNftMetadata.IsEmpty())
            {
                HUD.WrappedLabel(TEXT("NFT 情報ハッシュ（申請）: ")+Wallet->JoinPreviewNftMetadata,PreviewX+20*S,PreviewY+194*S,.38*S,Muted,PreviewW-40*S,18*S,2);
                HUD.WrappedLabel(TEXT("装備ロール ID（申請）: ")+Wallet->JoinPreviewNftRole,PreviewX+20*S,PreviewY+235*S,.38*S,Muted,PreviewW-40*S,18*S,2);
                HUD.WrappedLabel(TEXT("返還規則（申請）: ")+Wallet->JoinPreviewNftPolicy,PreviewX+20*S,PreviewY+276*S,.38*S,Muted,PreviewW-40*S,18*S,2);
            }
            HUD.Label(TEXT("手数料負担の申請: ")+Wallet->JoinPreviewFeePayer,PreviewX+20*S,PreviewY+316*S,.40*S,Ivory);
            HUD.WrappedLabel(TEXT("手数料上限明細（申請）: ")+Wallet->JoinPreviewFeeCaps,PreviewX+20*S,PreviewY+342*S,.36*S,Ivory,PreviewW-40*S,18*S,5);
            HUD.Label(TEXT("死亡時の損失・最大損失: 未確認"),PreviewX+20*S,PreviewY+439*S,.43*S,Gold);
            HUD.Label(TEXT("一部表示：台帳の試合規則・残高・所有権は未照合。"),PreviewX+20*S,PreviewY+462*S,.36*S,Muted);
            if(G->bEnglishSubtitles)
                HUD.WrappedLabel(TEXT("Partial, unverified terms. Death loss and maximum loss unavailable; no wallet approval."),PreviewX+20*S,PreviewY+485*S,.35*S,Muted,PreviewW-40*S,16*S,2);
            HUD.Label(TEXT("この画面から署名・入金はできません。"),PreviewX+20*S,PreviewY+520*S,.36*S,Teal);
        }
        if(Wallet->State==EArenaWalletState::AwaitingApproval&&Wallet->WalletQrTexture)
        {
            const int32 Pixels=Wallet->WalletQrTexture->GetSizeX();
            const int32 IntegerScale=FMath::Min(3,FMath::FloorToInt((W-1260*S)/FMath::Max(Pixels,1)));
            if(IntegerScale>=1)
            {
                const float Size=Pixels*IntegerScale;
                const float QX=FMath::FloorToFloat(W-Size-25*S),QY=FMath::FloorToFloat(210*S);
                HUD.DrawTextureSimple(Wallet->WalletQrTexture,QX,QY,static_cast<float>(IntegerScale),false);
                HUD.Label(TEXT("接続用 QR / この画面のみ"),QX,QY+Size+12*S,.36*S,Muted);
            }
            else HUD.Label(TEXT("QR 表示には画面を広げてください"),L,902*S,.42*S,Muted);
        }
    }
    HUD.Label(TEXT("ウォレット接続は資産の預入ではありません。対戦決済・NFT 売買は未公開です。"),L,940*S,.42*S,Muted);
    HUD.Label(TEXT("日本語・英語字幕付き。全八章の試作戦闘 / 音声未収録。環境素材：Powered by Poly Haven (CC0)"),L,970*S,.38*S,Muted);
    if(TitleArt) HUD.Label(TEXT("背景：生成キービジュアル / ゲーム画面ではありません"),W-600*S,100*S,.35*S,Muted);
    if(auto* Kernel=HUD.GetWorld()->GetGameInstance()->GetSubsystem<UArenaKernelSubsystem>()) HUD.Label(Kernel->StatusText,W-690*S,53*S,.34*S,Muted);
    if(G->bConfirmNewCampaign)
    {
        // Starting over erases the saved story, so it needs a second press.
        const float CW=FMath::Min(W-40*S,860*S),CH=(G->bEnglishSubtitles?280:200)*S;
        const float CX=(W-CW)*.5f,CY=(H-CH)*.5f;
        HUD.Panel(0,75*S,W,H,FLinearColor(0,0,0,.45f));
        HUD.Panel(CX,CY,CW,CH,FLinearColor(.013,.027,.033,.98f));
        HUD.Label(TEXT("はじめからやり直しますか？"),CX+30*S,CY+20*S,.9*S,Gold);
        float PromptY=CY+75*S;
        PromptY+=HUD.WrappedLabel(TEXT("保存した章・復旧記録・到達した章をすべて消去します。"),CX+30*S,PromptY,JapaneseSubtitleScale,Ivory,CW-60*S,JapaneseSubtitleLineHeight,2)*JapaneseSubtitleLineHeight+10*S;
        if(G->bEnglishSubtitles)
            PromptY+=HUD.WrappedLabel(TEXT("Start over? The saved chapter, checkpoint and chapter progress will be erased."),CX+30*S,PromptY,EnglishSubtitleScale,Muted,CW-60*S,EnglishSubtitleLineHeight,2)*EnglishSubtitleLineHeight+14*S;
        HUD.Label(TEXT("もう一度 N（パッド Y）で消去して開始   Esc（Start）で取り消し"),CX+30*S,PromptY,.5*S,Teal);
        if(G->bEnglishSubtitles) HUD.Label(TEXT("Press N (pad Y) again to erase and start over. Esc (Start) cancels."),CX+30*S,PromptY+30*S,.42*S,Muted);
    }
}
