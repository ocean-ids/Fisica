import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from '../navbar/navbar.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-dashboard',
  imports: [RouterOutlet, NavbarComponent, SidebarComponent, CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  sidebarVisible: boolean = true;

  ngOnInit(): void {
    
    const stored = localStorage.getItem('sidebarVisible');
    if (stored !== null) {
      this.sidebarVisible = stored === 'true';
    }
  }

  toggleSidebar(): void {
    this.sidebarVisible = !this.sidebarVisible;
    // Persistir preferencia del usuario
    localStorage.setItem('sidebarVisible', String(this.sidebarVisible));
  }
}
