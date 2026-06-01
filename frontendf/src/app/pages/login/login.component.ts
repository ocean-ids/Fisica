import { CommonModule, NgOptimizedImage } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { Router, RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule, NgOptimizedImage, RouterModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent implements OnInit, OnDestroy {
  username: string = '';
  password: string = '';
  isLoading: boolean = false;
  activeImageIndex = 0;
  isFading = false;
  private carouselTimer: any = null;
  private transitionTimer: any = null;
  private readonly fadeDurationMs = 1200;
  private readonly intervalMs = 6000;

  images: string[] = [
    'assets/images/fondo.png',
  ];

  get currentBackground(): string {
    const url = this.images[this.activeImageIndex] || this.images[0];
    return `url('${url}')`;
  }


  constructor(
    private authService: AuthService,
    private router: Router
  ) {}
  

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.router.navigateByUrl('/dashboard', { replaceUrl: true });
    }
    this.startCarousel();
  }

  ngOnDestroy(): void{
    this.stopCarousel();
  }

  private startCarousel(): void {
    if (this.images.length < 2) return;
    this.carouselTimer = setInterval(() => {
      this.beginFade();
    }, this.intervalMs);
  }

  private beginFade(): void {
    if (this.images.length < 2) return;
    this.isFading = true;
    if (this.transitionTimer) {
      clearTimeout(this.transitionTimer);
    }
    this.transitionTimer = setTimeout(() => {
      this.activeImageIndex = this.getNextIndex(this.activeImageIndex);
      requestAnimationFrame(() => {
        this.isFading = false;
      });
    }, this.fadeDurationMs);
  }

  private getNextIndex(index: number): number {
    return (index + 1) % this.images.length;
  }

  private stopCarousel(): void {
    if (this.carouselTimer){
      clearInterval(this.carouselTimer);
      this.carouselTimer = null;
    }
    if (this.transitionTimer) {
      clearTimeout(this.transitionTimer);
      this.transitionTimer = null;
    }
  }

  onSubmit(): void {
    if (!this.username || !this.password) {
      Swal.fire({
        icon: 'warning',
        title: 'Datos incompletos',
        text: 'Por favor, ingresa usuario y contraseña'
      });
      return;
    }

    this.isLoading = true;

    this.authService.login(this.username, this.password).subscribe({
      next: (response) =>  {
        console.log(`Acceso Exitoso`, response);
        const displayName = (response?.user?.full_name ||
          `${response?.user?.first_name ?? ''} ${response?.user?.last_name ?? ''}`
        ).trim() || this.username;
        Swal.fire({
          icon: 'success',
          title: 'Acceso exitoso',
          text: `Bienvenido ${displayName}`,
          timer: 1200,
          showConfirmButton: false
        }).then(() => {
          this.router.navigateByUrl('/dashboard', { replaceUrl: true });
        });
      },
      error: (error) => {
        console.log('Error de login', error);
        Swal.fire({
          icon: 'error',
          title: 'Error de login',
          text: 'Usuario o contraseña incorrectos'
        });
        this.isLoading = false;
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }
}
