  import React from 'react'
  import { useState } from 'react'
  import './Home.scss'

  function Home() {
      const notes = Array.from({ length: 8 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 5,
        duration: 10 + Math.random() * 6,
        symbol: i % 2 === 0 ? '♪' : '♫'
      }));
    return (
      <div>
        <div className="gradient">
          {notes.map(note => (
            <div
              key={note.id}
              className="music-note"
              style={{
                left: `${note.left}%`,
                animationDuration: `${note.duration}s`,
                animationDelay: `${note.delay}s`
            }}>
              {note.symbol}
            </div>
          ))}
          <div className="hero-text">
            <h1 className = "hero-title">your life’s soundtrack, <span id = "decoded">decoded</span></h1>
            <h2>see what moves you</h2>
            <a href={`${import.meta.env.VITE_LOGIN_URL}`} className="button">
              <span>log into spotify</span>
            </a>
          </div>
          
        </div>
      </div>
    )
  }

  export default Home