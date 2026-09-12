import InstallCommand from './InstallCommand';

const repo = 'https://github.com/tobiwsa/whisplet';

function Mark({ small = false }: { small?: boolean }) {
  return <svg className={small ? 'mark small' : 'mark'} viewBox="0 0 100 100" fill="none" aria-hidden="true"><path d="M10 50C20 5 30 95 40 50C50 5 60 95 70 50" stroke="currentColor" strokeWidth="7.5" strokeLinecap="round"/><path d="M88 24V76" stroke="#222330" strokeWidth="7" strokeLinecap="round"/></svg>;
}

export default function Home() {
  return (
    <>
      <header className="nav wrap">
        <a className="wordmark" href="#" aria-label="Whisplet home"><Mark small />Whisplet</a>
        <nav aria-label="Main navigation"><a href="#how-it-works">How it works</a><a href="#questions">Questions</a><a className="nav-github" href={repo}>GitHub <span aria-hidden="true">↗</span></a></nav>
      </header>
      <main>
        <section className="hero wrap">
          <div className="hero-copy">
            <p className="eyebrow"><span /> FOR YOUR MAC. FOR YOUR WORDS.</p>
            <h1>Think it.<br />Say it.<br /><em>There it is.</em></h1>
            <p className="intro">Your voice, turned into text. Right on your Mac.<br className="desktop-break" /> No account. No subscription. Just your words.</p>
            <div className="actions"><a className="button primary" href="#install">Get Whisplet <span aria-hidden="true">↗</span></a><a className="quiet-link" href="#how-it-works">Meet your new shortcut <span aria-hidden="true">↓</span></a></div>
            <p className="compatibility">Apple Silicon · macOS 14+ · Source-build preview</p>
          </div>
          <div className="hero-demo" aria-label="Illustration of speaking a thought into a writing app">
            <div className="note-window">
              <div className="window-bar"><div className="traffic"><i /><i /><i /></div><span>A thought worth keeping</span><span className="window-menu">···</span></div>
              <div className="note-body"><p className="note-date">WEDNESDAY, 10:00 AM</p><h2>Room to think.</h2><p>Let’s take a walk after lunch. I have a few ideas for the next project, and they sound better out loud.<span className="caret" /></p><span className="note-foot">Written at the speed of a thought.</span></div>
            </div>
            <div className="recording-pill"><span className="recording-dot"/><span className="wave" aria-hidden="true">{[9,17,28,14,36,23,40,19,31,12,26,38,17,28,10,20,31,16,8].map((height,i)=><i key={i} style={{height,animationDelay:`${i * -.09}s`}} />)}</span><span className="pill-key">F5</span></div>
            <div className="demo-caption"><span className="curved-arrow" aria-hidden="true">↖</span> Hold. Speak. Release.</div>
          </div>
        </section>
        <section className="principles wrap" aria-label="What makes Whisplet different"><p><span>01</span> Local by design</p><p><span>02</span> A shortcut away</p><p><span>03</span> Yours to change</p></section>
        <section className="details wrap" id="how-it-works">
          <div className="section-heading"><p className="eyebrow">LESS FRICTION, MORE THOUGHT</p><h2>A small app.<br />A little more freedom.</h2><p>For the message you don’t want to type.<br />The idea you don’t want to lose.</p></div>
          <div className="feature-list">
            <article><div className="feature-number">01</div><div><h3>Keep the conversation on your Mac.</h3><p>Parakeet turns your speech into text using your Mac’s own hardware. After the initial model download, dictation works offline.</p></div></article>
            <article><div className="feature-number">02</div><div><h3>One key. A lot less typing.</h3><p>Hold F5, speak, then release to insert into your text field. Prefer Right Option or Fn? Choose the shortcut that feels right.</p></div></article>
            <article><div className="feature-number">03</div><div><h3>Your words, your preferences.</h3><p>Add names to your dictionary. Save recordings locally if you want them. Optional S1-mini cleanup is there when you need it, and off by default.</p></div></article>
          </div>
        </section>
        <section className="install-section wrap" id="install">
          <div><p className="eyebrow">OPEN SOURCE. OPEN POSSIBILITIES.</p><h2>Make yourself<br /><em>heard.</em></h2><p>This early version builds on your Mac.<br />Bring a coding agent, or follow the guide.</p><a className="button primary" href={`${repo}/blob/main/docs/INSTALL.md`}>Open the install guide <span aria-hidden="true">↗</span></a></div>
          <div className="install-card"><div className="install-card-title"><Mark small /><span>Give your agent a little direction.</span></div><InstallCommand /><div className="install-notes"><p>Apple Silicon · macOS 14 or later</p><p>No paid Apple Developer membership needed for a local build. macOS permissions still apply.</p><a href={`${repo}/blob/main/AGENTS.md`}>Read AGENTS.md <span aria-hidden="true">↗</span></a></div></div>
        </section>
        <section className="faq wrap" id="questions"><h2>A few things<br />you might wonder.</h2><div>
          <details><summary>Does my audio leave my Mac?<span>+</span></summary><p>Recognition and optional cleanup happen locally. The first setup downloads tools and models; it does not send your recordings for transcription. Recording history is optional and stored on your Mac.</p></details>
          <details><summary>Is there a download-and-open app?<span>+</span></summary><p>This release is a source-build preview. The guide helps you compile and install it locally. A notarized Whisplet download and automatic binary updates are not available yet.</p></details>
          <details><summary>How do updates work?<span>+</span></summary><p>Run the update script in your clone, or ask your agent to follow AGENTS.md. It pulls the latest changes from your tracking branch, rebuilds the app and preserves your saved data. No update server or app account is needed.</p></details>
          <details><summary>Why does F5 open Apple Dictation?<span>+</span></summary><p>macOS may assign the physical F5 key to a system action. Use Fn+F5, or enable standard function keys in Keyboard settings. Then choose F5 hold in Whisplet’s Settings.</p></details>
          <details><summary>Is this related to Phonon?<span>+</span></summary><p>Yes. Whisplet is a GPL-3.0 fork of Phonon by Elliot Arledge / Infatoshi, with a new interface, optional S1-mini cleanup and local decoder optimizations. Model licenses are documented in the repository.</p></details>
        </div></section>
      </main>
      <footer className="wrap"><a className="wordmark" href="#"><Mark small />Whisplet</a><p>A little less typing. A little more you.</p><div><a href={repo}>Source ↗</a><a href="https://github.com/Infatoshi/phonon">Built on Phonon ↗</a></div></footer>
    </>
  );
}
