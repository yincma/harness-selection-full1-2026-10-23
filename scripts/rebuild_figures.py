"""Re-render published sources only; no Kiro execution and no model calls."""
from pathlib import Path
import argparse, asyncio, json, shutil
ROOT=Path(__file__).resolve().parents[1]
COLORS={'A':'#596F83','B':'#007F91','Bx4':'#AD7100','C':'#A6435C'}
INK,MUTED,PAPER,GRID='#172D3D','#526674','#F6F5F0','#D9E0E1'
HERE=ROOT/'rebuilt'
FONT=None
CHROMIUM_EXECUTABLE=None

def chart():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FixedLocator, FuncFormatter
    import logging
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    if FONT:
        font_manager.fontManager.addfont(FONT)
        family=font_manager.FontProperties(fname=FONT).get_name()
    else:
        family='sans-serif'
    plt.rcParams.update({'font.family':family,'axes.unicode_minus':False,'svg.fonttype':'none',
                         'font.size':17,'axes.labelsize':18,'xtick.labelsize':16,'ytick.labelsize':16})
    data=json.loads((ROOT/'plot-data.json').read_text())
    fig,axes=plt.subplots(2,1,figsize=(12,13.5),dpi=160)
    fig.patch.set_facecolor(PAPER)
    fig.subplots_adjust(left=.13,right=.96,bottom=.145,top=.88,hspace=.53)
    fig.text(.07,.965,'额外调用，换来了多少隐藏通过率？',fontsize=27,weight='bold',color=INK)
    fig.text(.07,.925,'正式结果保留静态检查；重复范围与敏感性分析分别标出',fontsize=17,color=MUTED)
    markers={'A':'o','B':'s','Bx4':'D','C':'^'}
    for ax,task,title in zip(axes,['commonmark','jsonschema'],['CommonMark','JSON Schema']):
        d=data[task];ax.set_facecolor('white');ax.set_xscale('log');ax.set_xlim(.25,50);ax.set_ylim(-3,106)
        ax.set_yticks([0,20,40,60,80,100]);ax.xaxis.set_major_locator(FixedLocator([.3,1,3,10,30]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:g}'))
        ax.grid(axis='y',color=GRID,linewidth=.8);ax.grid(axis='x',color=GRID,linewidth=.5,alpha=.5)
        ax.spines[['top','right']].set_visible(False)
        ax.spines[['left','bottom']].set_color('#9DAAB0')
        ax.set_title(title,loc='left',fontsize=23,weight='bold',color=INK,pad=20)
        ax.set_xlabel('调用积分 credits（对数刻度）',labelpad=10);ax.set_ylabel('隐藏测试通过率（%）',labelpad=10)
        bx=d['groups']['B']['credits'];lo=min(d['B_runs'].values());hi=max(d['B_runs'].values())
        ax.vlines(bx,lo,hi,color=INK,linewidth=3.4,zorder=3)
        ax.hlines([lo,hi],bx/.93,bx*.93,color=INK,linewidth=2.3,zorder=3)
        if task=='commonmark':
            ax.vlines(bx,38.2,49.2,color='#7E5895',linewidth=2.3,linestyle=(0,(3,2)),zorder=5)
            ax.hlines([38.2,49.2],bx/.87,bx*.87,color='#7E5895',linewidth=2,linestyle='--',zorder=5)
            ax.annotate('B 四次正式范围\n0–45.1',xy=(bx,12),xytext=(2.0,7),fontsize=16,color=INK,
                        arrowprops={'arrowstyle':'-','color':MUTED,'lw':1})
            ax.annotate('敏感性范围 38.2–49.2\n移除静态检查；不替代正式值',xy=(bx,49.2),xytext=(.38,86),fontsize=16,color='#7E5895',
                        arrowprops={'arrowstyle':'-','color':'#7E5895','lw':1,'connectionstyle':'angle3,angleA=0,angleB=90'})
            positions={'A':(.95,28),'B':(2.0,60),'Bx4':(21,22),'C':(30,73)}
            verdict='C 对 Bx4：未检出差异'
        else:
            ax.axhline(59,color='#7B858B',linestyle=(0,(5,4)),linewidth=1.6,zorder=1)
            ax.text(.30,61,'空实现保底线 59%',fontsize=16,color=MUTED)
            positions={'A':(.47,79),'B':(3.6,73),'Bx4':(14,73),'C':(30,43)}
            verdict='正式判定：Bx4 优于 C'
            ax.annotate('B 四次范围 94.4–96.4',xy=(bx,94.4),xytext=(1.4,101),fontsize=15,color=INK,
                        arrowprops={'arrowstyle':'-','color':MUTED,'lw':1})
        for key in ['A','B','Bx4','C']:
            g=d['groups'][key];x,y=g['credits'],g['score'];color=COLORS[key]
            ax.scatter([x],[y],c=color,s=115,marker=markers[key],edgecolor='white',linewidth=1.2,zorder=8)
            ax.annotate(f'{key}  {y:.1f}%\n{x:.2f} credits',xy=(x,y),xytext=positions[key],
                        textcoords='data',ha='center',va='center',fontsize=16,color=color,weight='bold',
                        bbox={'boxstyle':'round,pad=.12','facecolor':'white','edgecolor':'none','alpha':1},
                        arrowprops={'arrowstyle':'-','color':color,'lw':1.1})
        ax.text(1,.999,verdict,transform=ax.transAxes,ha='right',va='bottom',fontsize=16,color=INK)
    fig.text(.07,.055,'实心点：正式结果；实线：B 四次最小—最大；虚线：敏感性范围 / 保底线',fontsize=16,color=INK)
    fig.text(.07,.024,'范围置于 B_1 积分处，非逐次积分分布。来源：full1 + 素材包 §8.4。',fontsize=15,color=MUTED)
    fig.savefig(HERE/'fig-04-quality-credits.png',dpi=160,facecolor=fig.get_facecolor())
    fig.savefig(HERE/'fig-04-quality-credits.svg',facecolor=fig.get_facecolor())
    plt.close(fig)

async def capture():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        launch={'headless':True}
        if CHROMIUM_EXECUTABLE:launch['executable_path']=CHROMIUM_EXECUTABLE
        browser=await p.chromium.launch(**launch)
        page=await browser.new_page(viewport={'width':1280,'height':1000},device_scale_factor=1)
        for src,dst in [('fig-02-record-reader.html','fig-02-execution-records.png'),('fig-03-task-reader.html','fig-03-task-examples.png')]:
            await page.goto((ROOT/src).as_uri())
            await page.evaluate('document.fonts.ready')
            await page.screenshot(path=str(HERE/dst),full_page=True)
        await page.set_viewport_size({'width':1600,'height':1110})
        await page.set_content('<html><meta charset="utf-8"><body style="margin:0">'+(ROOT/'fig-01-workflows.svg').read_text()+'</body></html>')
        await page.evaluate('document.fonts.ready')
        await page.locator('svg').screenshot(path=str(HERE/'fig-01-workflows.png'))
        await browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--font')
    parser.add_argument('--output',default='rebuilt')
    parser.add_argument('--chart-only',action='store_true')
    parser.add_argument('--browser-executable',help='Optional local Chrome/Chromium executable')
    args=parser.parse_args()
    FONT=args.font
    CHROMIUM_EXECUTABLE=args.browser_executable
    HERE=Path(args.output).resolve()
    if HERE==ROOT:raise SystemExit('Choose a separate output directory to preserve published files.')
    HERE.mkdir(parents=True,exist_ok=True)
    chart()
    shutil.copyfile(ROOT/'fig-01-workflows.svg',HERE/'fig-01-workflows.svg')
    if not args.chart_only:asyncio.run(capture())
    print('Rendered published sources into',HERE)
