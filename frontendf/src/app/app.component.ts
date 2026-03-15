import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  title = 'frontendf';

  ngOnInit(): void {
    const storedTheme = localStorage.getItem('themeMode');
    const themeMode = storedTheme === 'dark' ? 'dark' : 'light';
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${themeMode}`);
  }
}
