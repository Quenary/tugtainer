import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ImageCardGeneralComponent } from './image-card-general.component';

describe('ImageCardGeneralComponent', () => {
  let component: ImageCardGeneralComponent;
  let fixture: ComponentFixture<ImageCardGeneralComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImageCardGeneralComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ImageCardGeneralComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
